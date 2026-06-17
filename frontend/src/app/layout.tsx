import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aciono Você - Lista Telefônica HCFMB",
  description: "Lista telefônica offline-first do HCFMB / UNESP",
  manifest: "/manifest.json",
  themeColor: "#008B95",
  viewport: "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Aciono Você",
  },
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>
        {children}
      </body>
    </html>
  );
}
