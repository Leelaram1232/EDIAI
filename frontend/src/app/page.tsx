"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    router.replace(token ? "/chat" : "/login");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-pulse">
        <div className="text-2xl font-bold gradient-text">Loading AIEP...</div>
      </div>
    </div>
  );
}
