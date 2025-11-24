"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [popup, setPopup] = useState<Window | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [location, setLocation] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [mounted, setMounted] = useState(false);
  const [playingAudio, setPlayingAudio] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // const PORT = 8000
  const PYTHON_URL = process.env.NEXT_PUBLIC_BASE_PYTHON_URL;

  useEffect(() => {
    const token = localStorage.getItem("authToken");
    if (!token) {
      router.push("/");
      return;
    }
    setMounted(true);

    // Fetch geolocation
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
        },
        (err) => console.log("Geolocation error:", err)
      );
    }
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data === "google-auth-success") {
        setError(null);
        setPopup((prev) => {
          if (prev) prev.close();
          return null;
        });
      }
      if (event.data === "google-auth-failed") {
        setError("OAuth authentication failed");
        setPopup((prev) => {
          if (prev) prev.close();
          return null;
        });
      }
    };

    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  const getAuthToken = () => localStorage.getItem("authToken") || "";

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/wav" });
        uploadAudio(blob);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      setError("Microphone access denied");
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadAudio = async (blob: Blob) => {
    setLoading(true);
    const formData = new FormData();
    formData.append("audio", blob, "recording.wav");

    try {
      const response = await fetch(`${PYTHON_URL}/audio`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });

      if (!response.ok) throw new Error("Audio upload failed");

      const data = await response.json();
      setInput(data.Transcription || "");
    } catch (err) {
      setError("Failed to transcribe audio");
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (selectedImage && input.trim()) {
      await handleImageWithText(selectedImage, input);
      return;
    }

    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${PYTHON_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({
          text: userMessage.content,
          ...(location && { location }),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.message || data.response || JSON.stringify(data),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      setError("Failed to send message: " + errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthClick = (url: string) => {
    const authUrl = url.includes("?")
      ? `${url}&token=${encodeURIComponent(getAuthToken())}`
      : `${url}?token=${encodeURIComponent(getAuthToken())}`;

    const newPopup = window.open(
      authUrl,
      "google-oauth-popup",
      "width=500,height=650"
    );
    if (!newPopup) {
      setError("Popup blocked! Please allow popups for this site.");
      return;
    }
    setPopup(newPopup);
  };

  const handleTextToSpeech = async (text: string, messageId: string) => {
    if (playingAudio === messageId) {
      setPlayingAudio(null);
      return;
    }

    try {
      const response = await fetch(`${PYTHON_URL}/tts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) throw new Error("Text-to-speech failed");

      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);

      setPlayingAudio(messageId);
      audio.onended = () => setPlayingAudio(null);
      audio.play();
    } catch (err) {
      setError("Failed to convert text to speech");
    }
  };

  const handleImageWithText = async (file: File, text: string) => {
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${PYTHON_URL}/upload_image`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });

      if (!response.ok) throw new Error("Image upload failed");

      const { image_path } = await response.json();

      // 2️⃣ Add the user message to chat immediately
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content: `[🖼️Image attached]\n${text}`,
      };
      setMessages((prev) => [...prev, userMessage]);

      // 3️⃣ Call the image processing endpoint
      const processingRes = await fetch(`${PYTHON_URL}/image_processing`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({
          text,
          image: image_path,
        }),
      });

      const processingData = await processingRes.json();

      // 4️⃣ Add assistant message with the result
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `[🖼️Image processed]: ${JSON.stringify(processingData)}`,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError("Failed to process image");
    } finally {
      // 5️⃣ Reset UI
      setLoading(false);
      setInput("");
      setSelectedImage(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleImageSelect = (file: File) => {
    setSelectedImage(file);
  };

  const renderMessage = (content: string) => {
    const urlRegex = /(http:\/\/(?:localhost|127\.0\.0\.1):\d+\/auth[^\s]*)/g;
    const parts = content.split(urlRegex);

    return parts.map((part, idx) => {
      if (part.match(urlRegex)) {
        return (
          <button
            key={idx}
            onClick={() => handleAuthClick(part)}
            className="text-blue-500 hover:text-blue-700 underline font-medium break-all"
          >
            Click here to authenticate
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    router.push("/");
  };

  if (!mounted) {
    return null;
  }

  return (
    <main className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="bg-card border-b border-border p-4">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold text-foreground">Chat Assistant</h1>
          <Button variant="outline" onClick={handleLogout}>
            Logout
          </Button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto py-6 px-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground py-12">
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm">
                Type a message or use the microphone to record
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div className="flex flex-col gap-2">
                <Card
                  className={`max-w-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-muted text-foreground"
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap break-words">
                    {renderMessage(msg.content)}
                  </div>
                </Card>
                {msg.role === "assistant" && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleTextToSpeech(msg.content, msg.id)}
                    className="text-xs w-fit"
                  >
                    {playingAudio === msg.id ? "⏸ Stop" : "🔊 Speak"}
                  </Button>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <Card className="bg-muted text-foreground px-4 py-3">
                <div className="flex gap-2 items-center">
                  <div className="w-2 h-2 rounded-full bg-foreground animate-bounce"></div>
                  <div
                    className="w-2 h-2 rounded-full bg-foreground animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 rounded-full bg-foreground animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                </div>
              </Card>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="max-w-4xl mx-auto w-full px-4">
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-border bg-card p-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <Input
            type="text"
            placeholder={
              selectedImage
                ? "Add text to describe the image..."
                : "Type your message..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) =>
              e.key === "Enter" && !e.shiftKey && handleSendMessage()
            }
            disabled={loading || isRecording}
            className="flex-1"
          />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleImageSelect(file);
            }}
            className="hidden"
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            variant="outline"
            disabled={loading || isRecording}
            className={selectedImage ? "bg-blue-100 border-blue-500" : ""}
          >
            {selectedImage ? "✓ 🖼" : "🖼 Image"}
          </Button>
          <Button
            onClick={isRecording ? handleStopRecording : handleStartRecording}
            variant="outline"
            disabled={loading}
          >
            {isRecording ? "⏹ Stop" : "🎙 Record"}
          </Button>
          <Button
            onClick={handleSendMessage}
            disabled={loading || (!input.trim() && !selectedImage)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Send
          </Button>
        </div>
      </div>
    </main>
  );
}
