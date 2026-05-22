import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Thane Surge | Q-Commerce SLA Engine",
  description: "10-minute grocery delivery surge pricing & SLA prediction for Thane, Mumbai",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link href="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.css" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
