import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/store/auth";

export const metadata: Metadata = {
  title: "KOICA - AI Chat Platform",
  description: "Korea International Cooperation Agency - AI Chat Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

