import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Aetherville',
  description: 'AI society simulator client shell'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
