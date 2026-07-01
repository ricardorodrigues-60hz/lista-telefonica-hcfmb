import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aciono Você - Lista Telefônica HCFMB",
  description: "Lista telefônica offline-first do HCFMB / UNESP",
  manifest: "/lista-telefonica/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Aciono Você",
  },
  icons: {
    icon: "/lista-telefonica/icon.svg",
    apple: "/lista-telefonica/icon.svg",
  }
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#008B95",
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
