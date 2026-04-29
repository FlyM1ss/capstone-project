"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, Mic, MicOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SearchTips } from "./search-tips";

interface SpeechRecognitionEvent {
  results: { [index: number]: { [index: number]: { transcript: string } }; length: number };
  resultIndex: number;
}

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
};

function getSpeechRecognition(): (new () => SpeechRecognitionInstance) | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as Record<string, unknown>).SpeechRecognition ??
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition
  ) as (new () => SpeechRecognitionInstance) | null;
}

export function SearchBar({ defaultValue = "" }: { defaultValue?: string }) {
  const [query, setQuery] = useState(defaultValue);
  const [listening, setListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const router = useRouter();

  useEffect(() => {
    setSpeechSupported(getSpeechRecognition() !== null);
  }, []);

  const handleSearch = useCallback(
    (q: string) => {
      if (q.trim()) {
        router.push(`/search?q=${encodeURIComponent(q.trim())}`);
      }
    },
    [router]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch(query);
  };

  const toggleListening = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognition = getSpeechRecognition();
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      handleSearch(transcript);
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
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl">
      <div className="relative flex items-center">
        <Search className="absolute left-3 h-5 w-5 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search Deloitte resources..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 pr-28 h-12 text-base"
        />
        <div className="absolute right-2 flex items-center gap-1">
          {speechSupported && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={toggleListening}
              className={listening ? "text-destructive" : "text-muted-foreground"}
              aria-label={listening ? "Stop recording" : "Start voice search"}
            >
              {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            </Button>
          )}
          <SearchTips />
          <Button type="submit" size="sm" disabled={!query.trim()}>
            Search
          </Button>
        </div>
      </div>
    </form>
  );
}
