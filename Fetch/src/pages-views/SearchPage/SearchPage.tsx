import { useState, useRef, useEffect } from 'react';
import { FileType, SearchFilters } from '@/types';
import { useUser } from '@/context/UserContext';
import Greeting from '@/components/Greeting/Greeting';
import SearchBar from '@/components/SearchBar/SearchBar';
import FilterControls from '@/components/FilterControls/FilterControls';
import styles from './SearchPage.module.scss';

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: SpeechRecognitionResultList }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};

function getSpeechRecognition(): (new () => SpeechRecognitionInstance) | null {
  if (typeof window === 'undefined') return null;
  return (
    (window as unknown as Record<string, unknown>).SpeechRecognition ??
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition
  ) as (new () => SpeechRecognitionInstance) | null ?? null;
}

export default function SearchPage() {
  const user = useUser();
  const [filters, setFilters] = useState<SearchFilters>({
    types: ['pptx', 'pdf', 'docx'],
    authorized: 'all',
  });
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState<string | undefined>(undefined);
  const [speechSupported] = useState(() => getSpeechRecognition() !== null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  // Clean up recognition on unmount
  useEffect(() => () => { recognitionRef.current?.stop(); }, []);

  function toggleListening() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognition = getSpeechRecognition();
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (e) => {
      let text = '';
      for (let i = 0; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
      }
      setTranscript(text);
    };

    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };

    recognition.onerror = () => {
      setListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function toggleType(type: FileType) {
    setFilters((prev) => ({
      ...prev,
      types: prev.types.includes(type)
        ? prev.types.filter((t) => t !== type)
        : [...prev.types, type],
    }));
  }

  function setDateRange(start: string, end: string) {
    setFilters((prev) => ({ ...prev, dateRange: { start, end } }));
  }

  function setAuthorized(val: NonNullable<SearchFilters['authorized']>) {
    setFilters((prev) => ({ ...prev, authorized: val }));
  }

  return (
    <div className={styles.page}>
      <div className={styles.center}>
        <Greeting firstName={user?.firstName ?? 'there'} />

        <div className={styles.searchSection}>
          <SearchBar filters={filters} externalQuery={transcript} />

          <div className={styles.filterRow}>
            <FilterControls
              filters={filters}
              onToggleType={toggleType}
              onSetDateRange={setDateRange}
              onSetAuthorized={setAuthorized}
            />

            {speechSupported && (
              <button
                className={`${styles.voiceButton} ${listening ? styles.voiceButtonActive : ''}`}
                type="button"
                aria-label={listening ? 'Stop recording' : 'Voice search'}
                onClick={toggleListening}
              >
                <svg width="18" height="18" viewBox="0 0 98 98" fill="none" stroke="currentColor" strokeWidth="13.3333" strokeLinecap="round" strokeLinejoin="round">
                  {listening ? (
                    <>
                      {[
                        { x: 8.167,  y1: 40.833, y2: 53.083, delay: '0s'     },
                        { x: 24.5,   y1: 24.5,   y2: 69.417, delay: '0.15s'  },
                        { x: 40.834, y1: 12.25,  y2: 85.75,  delay: '0.3s'   },
                        { x: 57.167, y1: 32.667, y2: 61.25,  delay: '0.45s'  },
                        { x: 73.5,   y1: 20.417, y2: 73.5,   delay: '0.3s'   },
                        { x: 89.834, y1: 40.833, y2: 53.083, delay: '0.15s'  },
                      ].map((bar, i) => (
                        <line
                          key={i}
                          className={styles.waveAnimBar}
                          x1={bar.x} y1={bar.y1} x2={bar.x} y2={bar.y2}
                          style={{ animationDelay: bar.delay }}
                        />
                      ))}
                    </>
                  ) : (
                    <path d="M8.167 40.833V53.083M24.5 24.5V69.417M40.834 12.25V85.75M57.167 32.667V61.25M73.5 20.417V73.5M89.834 40.833V53.083" />
                  )}
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
