"use client";

import React, { useState, useEffect } from "react";
import {
  getIntelligenceStatus,
  configureIntelligence,
  testLlmConnection,
  IntelligenceStatus,
} from "@/lib/api";

interface IntelligenceConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigUpdated: (status: IntelligenceStatus) => void;
}

export default function IntelligenceConfigModal({
  isOpen,
  onClose,
  onConfigUpdated,
}: IntelligenceConfigModalProps) {
  const [mockLlm, setMockLlm] = useState<boolean>(true);
  const [provider, setProvider] = useState<string>("gemini");
  const [model, setModel] = useState<string>("gemini-3.5-flash-lite");
  const [apiKey, setApiKey] = useState<string>("");
  const [showKey, setShowKey] = useState<boolean>(false);
  const [tokensUsed, setTokensUsed] = useState<number>(0);

  const [testing, setTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    latencyMs?: number;
    message?: string;
  } | null>(null);

  const [saving, setSaving] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      getIntelligenceStatus()
        .then((st) => {
          setMockLlm(st.mode === "MOCK_LLM");
          setProvider(st.provider || "gemini");
          setModel(st.model || "gemini-3.5-flash-lite");
          setTokensUsed(st.totalTokensUsed || 0);
          setTestResult(null);
        })
        .catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Temporarily apply key in session if provided
      if (apiKey.trim()) {
        await configureIntelligence({
          mockLlm,
          provider,
          model,
          apiKey: apiKey.trim(),
        });
      }
      const res = await testLlmConnection();
      setTestResult({
        success: res.success,
        latencyMs: res.latencyMs,
        message: res.message,
      });
    } catch (e: any) {
      setTestResult({
        success: false,
        message: e?.message || "Connection test failed",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await configureIntelligence({
        mockLlm,
        provider,
        model,
        apiKey: apiKey.trim() || undefined,
      });
      onConfigUpdated(updated);
      onClose();
    } catch (e: any) {
      alert(`Failed to save configuration: ${e?.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4">
      <div className="bg-[#141418] border-4 border-black p-6 max-w-lg w-full shadow-[8px_8px_0px_#00E5FF]">
        {/* Header */}
        <div className="flex items-center justify-between border-b-2 border-zinc-800 pb-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-[#00E5FF] border border-black" />
              <h3 className="font-mono text-sm font-black text-white uppercase tracking-wider">
                INTELLIGENCE API & LLM REASONING CONFIG
              </h3>
            </div>
            <p className="font-mono text-[10px] text-zinc-400 mt-0.5">
              Switch between deterministic mock mode and live LiteLLM / Gemini reasoning
            </p>
          </div>
          <button
            onClick={onClose}
            className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-white font-mono text-xs font-black uppercase border border-black"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4 font-mono text-xs">
          {/* Mode Switcher */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-zinc-400 uppercase font-bold">REASONING ENGINE MODE</label>
              {tokensUsed > 0 && (
                <span className="text-[10px] text-[#CCFF00] font-black">
                  CUMULATIVE TOKENS: {tokensUsed.toLocaleString()}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setMockLlm(true)}
                className={`py-2 px-3 font-black uppercase border-2 border-black transition-all ${
                  mockLlm
                    ? "bg-[#CCFF00] text-black shadow-[2px_2px_0px_#000]"
                    : "bg-[#09090B] text-zinc-400 hover:text-white"
                }`}
              >
                MOCK DETERMINISTIC
              </button>
              <button
                type="button"
                onClick={() => setMockLlm(false)}
                className={`py-2 px-3 font-black uppercase border-2 border-black transition-all ${
                  !mockLlm
                    ? "bg-[#00E5FF] text-black shadow-[2px_2px_0px_#000]"
                    : "bg-[#09090B] text-zinc-400 hover:text-white"
                }`}
              >
                LIVE LLM REASONING
              </button>
            </div>
          </div>

          {/* Provider Selection */}
          <div>
            <label className="block text-zinc-400 uppercase font-bold mb-1">PROVIDER</label>
            <select
              value={provider}
              onChange={(e) => {
                const p = e.target.value;
                setProvider(p);
                if (p === "gemini") setModel("gemini-3.5-flash-lite");
                else if (p === "openai") setModel("gpt-4o-mini");
                else if (p === "anthropic") setModel("claude-3-5-sonnet-20241022");
              }}
              className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#00E5FF]"
            >
              <option value="gemini">Google Gemini (Recommended)</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic Claude</option>
            </select>
          </div>

          {/* Model Name */}
          <div>
            <label className="block text-zinc-400 uppercase font-bold mb-1">MODEL IDENTIFIER</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#00E5FF]"
            />
          </div>

          {/* Session API Key Input */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-zinc-400 uppercase font-bold">SESSION API KEY</label>
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="text-[10px] text-[#00E5FF] uppercase font-bold"
              >
                {showKey ? "HIDE" : "SHOW"}
              </button>
            </div>
            <input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste session API key (or set in .env)"
              className="w-full bg-[#09090B] border-2 border-zinc-700 p-2 text-white outline-none focus:border-[#00E5FF]"
            />
            <div className="text-[10px] text-zinc-500 mt-1">
              🔒 Key is stored in-memory for this session only; never logged or serialized to database.
            </div>
          </div>

          {/* Connection Test Result */}
          {testResult && (
            <div
              className={`p-2.5 border-2 ${
                testResult.success
                  ? "bg-[#CCFF00]/10 border-[#CCFF00] text-[#CCFF00]"
                  : "bg-[#FF2E4C]/10 border-[#FF2E4C] text-[#FF2E4C]"
              }`}
            >
              <div className="font-black uppercase text-[11px]">
                {testResult.success ? "✓ CONNECTION VERIFIED" : "✗ CONNECTION FAILED"}
                {testResult.latencyMs != null && ` (${testResult.latencyMs}ms)`}
              </div>
              <div className="text-[10px] text-zinc-300 mt-0.5">{testResult.message}</div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between gap-2 pt-2 border-t border-zinc-800">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-[#00E5FF] font-black uppercase border-2 border-black active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50"
            >
              {testing ? "TESTING..." : "TEST CONNECTION"}
            </button>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white font-black uppercase border-2 border-black"
              >
                CANCEL
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-[#00E5FF] hover:bg-[#33EAFF] text-black font-black uppercase border-2 border-black shadow-[3px_3px_0px_#000] active:translate-x-0.5 active:translate-y-0.5 disabled:opacity-50"
              >
                {saving ? "SAVING..." : "SAVE & APPLY"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
