"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Navbar } from "@/components/navbar";
import { Hero } from "@/components/hero";
import { TryOnStudio } from "@/components/try-on-studio";

export default function Home() {
  const [showStudio, setShowStudio] = useState(false);

  return (
    <div className="relative min-h-screen">
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-900/20 via-[#0a0a0f] to-[#0a0a0f] -z-10" />

      <Navbar onTryOn={() => setShowStudio(true)} />

      <AnimatePresence mode="wait">
        {!showStudio ? (
          <motion.div
            key="hero"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            <Hero onGetStarted={() => setShowStudio(true)} />
          </motion.div>
        ) : (
          <motion.div
            key="studio"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <TryOnStudio onBack={() => setShowStudio(false)} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
