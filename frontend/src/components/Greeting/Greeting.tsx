import { useGreeting } from '@/hooks/useGreeting';
import styles from './Greeting.module.scss';

interface Props {
  firstName: string;
}

export default function Greeting({ firstName }: Props) {
  const greeting = useGreeting();

  return (
    <h1 className={styles.greeting}>
      {greeting},{' '}
      <span className={styles.name}>{firstName}.</span>
    </h1>
  );
}
