"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useDropzone } from "react-dropzone";
import { ArrowLeft, Upload, Loader2, Download, RefreshCw, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TryOnStudioProps {
  onBack: () => void;
}

type Stage = "upload" | "processing" | "result";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8899";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "changeme-generate-a-real-key";

function DropZone({
  label,
  hint,
  image,
  onDrop,
}: {
  label: string;
  hint: string;
  image: string | null;
  onDrop: (file: File) => void;
}) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "image/jpeg": [], "image/png": [] },
    maxFiles: 1,
    onDrop: (files) => files[0] && onDrop(files[0]),
  });

  return (
    <div
      {...getRootProps()}
      className={`relative group cursor-pointer rounded-2xl border-2 border-dashed transition-all duration-300 overflow-hidden aspect-[3/4] flex items-center justify-center ${
        isDragActive
          ? "border-violet-500 bg-violet-500/10 scale-[1.02]"
          : image
          ? "border-transparent"
          : "border-white/10 hover:border-violet-500/50 bg-white/[0.02] hover:bg-white/[0.04]"
      }`}
    >
      <input {...getInputProps()} />
      {image ? (
        <>
          <img src={image} alt={label} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <p className="text-sm font-medium">Click to change</p>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center gap-3 p-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 flex items-center justify-center">
            {label === "Your Photo" ? (
              <Upload className="w-6 h-6 text-violet-400" />
            ) : (
              <ImageIcon className="w-6 h-6 text-fuchsia-400" />
            )}
          </div>
          <div>
            <p className="font-medium text-sm">{label}</p>
            <p className="text-xs text-zinc-500 mt-1">{hint}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export function TryOnStudio({ onBack }: TryOnStudioProps) {
  const [personImage, setPersonImage] = useState<string | null>(null);
  const [personFile, setPersonFile] = useState<File | null>(null);
  const [garmentImage, setGarmentImage] = useState<string | null>(null);
  const [garmentFile, setGarmentFile] = useState<File | null>(null);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("upload");
  const [error, setError] = useState<string | null>(null);
  const [processingTime, setProcessingTime] = useState<number>(0);

  const handlePersonDrop = useCallback((file: File) => {
    setPersonFile(file);
    setPersonImage(URL.createObjectURL(file));
    setResultImage(null);
    setStage("upload");
  }, []);

  const handleGarmentDrop = useCallback((file: File) => {
    setGarmentFile(file);
    setGarmentImage(URL.createObjectURL(file));
    setResultImage(null);
    setStage("upload");
  }, []);

  const handleTryOn = async () => {
    if (!personFile || !garmentFile) return;

    setStage("processing");
    setError(null);
    const startTime = Date.now();

    try {
      const formData = new FormData();
      formData.append("person_image", personFile);
      formData.append("garment_image", garmentFile);
      formData.append("category", "upper");

      const res = await fetch(`${API_URL}/v1/tryon/fast`, {
        method: "POST",
        headers: { "X-API-Key": API_KEY },
        body: formData,
      });

      const data = await res.json();

      if (!data.success) {
        throw new Error(data.error?.message || "Try-on failed");
      }

      const resultUrl = data.data.result_url;
      const imgRes = await fetch(resultUrl);
      const blob = await imgRes.blob();
      setResultImage(URL.createObjectURL(blob));
      setProcessingTime(Math.round((Date.now() - startTime) / 1000));
      setStage("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setStage("upload");
    }
  };

  const handleReset = () => {
    setPersonImage(null);
    setPersonFile(null);
    setGarmentImage(null);
    setGarmentFile(null);
    setResultImage(null);
    setStage("upload");
    setError(null);
  };

  const canGenerate = personFile && garmentFile && stage === "upload";

  return (
    <section className="pt-24 pb-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="text-zinc-400 hover:text-white rounded-full"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div className="h-4 w-px bg-white/10" />
          <h2 className="text-lg font-[family-name:var(--font-heading)] font-semibold">
            Try-On Studio
          </h2>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm"
          >
            {error}
          </motion.div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-3">
            <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
              Step 1 - Your Photo
            </label>
            <DropZone
              label="Your Photo"
              hint="Upload a full-body photo"
              image={personImage}
              onDrop={handlePersonDrop}
            />
          </div>

          <div className="space-y-3">
            <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
              Step 2 - Garment
            </label>
            <DropZone
              label="Garment"
              hint="Upload a clothing item"
              image={garmentImage}
              onDrop={handleGarmentDrop}
            />
          </div>

          <div className="space-y-3">
            <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
              Result
            </label>
            <div className="relative rounded-2xl border border-white/5 bg-white/[0.02] aspect-[3/4] flex items-center justify-center overflow-hidden">
              {stage === "processing" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center gap-4"
                >
                  <div className="relative">
                    <div className="w-16 h-16 rounded-full border-2 border-violet-500/30 border-t-violet-500 animate-spin" />
                    <Loader2 className="w-6 h-6 text-violet-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium">Generating try-on...</p>
                    <p className="text-xs text-zinc-500 mt-1">This takes about 15 seconds</p>
                  </div>
                </motion.div>
              )}

              {stage === "result" && resultImage && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                  className="w-full h-full"
                >
                  <img src={resultImage} alt="Try-on result" className="w-full h-full object-cover" />
                  <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
                    <span className="text-xs bg-black/60 backdrop-blur-sm px-3 py-1 rounded-full text-zinc-300">
                      {processingTime}s
                    </span>
                    <a
                      href={resultImage}
                      download="stilar-tryon.jpg"
                      className="text-xs bg-black/60 backdrop-blur-sm px-3 py-1 rounded-full text-zinc-300 hover:text-white transition-colors flex items-center gap-1"
                    >
                      <Download className="w-3 h-3" />
                      Save
                    </a>
                  </div>
                </motion.div>
              )}

              {stage === "upload" && !resultImage && (
                <div className="flex flex-col items-center gap-3 text-center p-6">
                  <div className="w-14 h-14 rounded-2xl bg-white/[0.03] flex items-center justify-center">
                    <Loader2 className="w-6 h-6 text-zinc-600" />
                  </div>
                  <p className="text-sm text-zinc-600">Result will appear here</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-center gap-4">
          {stage === "result" ? (
            <>
              <Button
                onClick={handleReset}
                variant="outline"
                className="rounded-full px-6 border-white/10 bg-white/5 hover:bg-white/10"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Try another
              </Button>
            </>
          ) : (
            <Button
              onClick={handleTryOn}
              disabled={!canGenerate}
              className="bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-30 disabled:cursor-not-allowed text-white border-0 rounded-full px-8 h-12 text-base font-medium shadow-2xl shadow-violet-500/30"
            >
              {stage === "processing" ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                "Generate Try-On"
              )}
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
