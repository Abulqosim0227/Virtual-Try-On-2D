"use client";

import { Sparkles } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-white/5 py-8 px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-zinc-500 text-sm">
          <Sparkles className="w-4 h-4" />
          <span>STILAR - AI Virtual Try-On for Uzbekistan</span>
        </div>
        <p className="text-xs text-zinc-600">
          Powered by CatVTON. Images are processed securely and deleted after use.
        </p>
      </div>
    </footer>
  );
}
