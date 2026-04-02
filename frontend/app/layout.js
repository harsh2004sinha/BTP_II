import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/authContext";
import { Toaster } from "react-hot-toast";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title:       "SolarOptima – Intelligent Energy Management",
  description: "AI-powered solar, battery, and grid optimization platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <AuthProvider>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#1e293b",
                color:      "#f1f5f9",
                border:     "1px solid #334155",
                borderRadius: "12px",
                fontSize:   "14px",
              },
              success: { iconTheme: { primary: "#10b981", secondary: "#f1f5f9" } },
              error:   { iconTheme: { primary: "#ef4444", secondary: "#f1f5f9" } },
            }}
          />
        </AuthProvider>
      </body>
    </html>
  );
}