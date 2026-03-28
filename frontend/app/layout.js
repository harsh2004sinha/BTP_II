import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "@/context/AuthContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "EnergyOptimizer - Smart Energy Management",
  description:
    "Optimize your energy usage with solar, battery, and grid management",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* Auth Context wraps everything */}
        <AuthProvider>
          {children}
          {/* Toast notifications - appears on top of everything */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#1E293B",
                color: "#F8FAFC",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "12px",
              },
              success: {
                iconTheme: {
                  primary: "#22C55E",
                  secondary: "#1E293B",
                },
              },
              error: {
                iconTheme: {
                  primary: "#EF4444",
                  secondary: "#1E293B",
                },
              },
            }}
          />
        </AuthProvider>
      </body>
    </html>
  );
}