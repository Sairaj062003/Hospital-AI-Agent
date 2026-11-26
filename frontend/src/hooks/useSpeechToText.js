import { useState, useRef, useCallback } from "react";
import * as sdk from "microsoft-cognitiveservices-speech-sdk";

const SPEECH_KEY = import.meta.env.VITE_AZURE_SPEECH_KEY;
const SPEECH_REGION = import.meta.env.VITE_AZURE_SPEECH_REGION;

export default function useSpeechToText() {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState(null);
  const [error, setError] = useState(null);

  const recognizerRef = useRef(null);
  const phrasesRef = useRef([]);

  const startListening = useCallback(() => {
    if (!SPEECH_KEY || !SPEECH_REGION) {
      setError("Azure Speech credentials are not configured.");
      return;
    }

    setError(null);
    setTranscript(null);
    phrasesRef.current = [];

    const speechConfig = sdk.SpeechConfig.fromSubscription(SPEECH_KEY, SPEECH_REGION);
    speechConfig.speechRecognitionLanguage = "en-US";

    const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
    const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);
    recognizerRef.current = recognizer;

    // Fires once per completed phrase/sentence (after a natural pause),
    // but the SESSION itself stays open until we call stopContinuousRecognitionAsync.
    recognizer.recognized = (_sender, event) => {
      if (event.result.reason === sdk.ResultReason.RecognizedSpeech && event.result.text) {
        phrasesRef.current.push(event.result.text);
      }
    };

    recognizer.canceled = (_sender, event) => {
      if (event.reason === sdk.CancellationReason.Error) {
        setError("Speech recognition error. Check your microphone and credentials.");
      }
      setListening(false);
      recognizer.close();
      recognizerRef.current = null;
    };

    recognizer.sessionStopped = () => {
      setListening(false);
      recognizer.close();
      recognizerRef.current = null;
    };

    recognizer.startContinuousRecognitionAsync(
      () => setListening(true),
      (err) => {
        setError("Could not start microphone. Please check permissions.");
        setListening(false);
        recognizerRef.current = null;
      }
    );
  }, []);

  const stopListening = useCallback(() => {
    const recognizer = recognizerRef.current;
    if (!recognizer) return;

    recognizer.stopContinuousRecognitionAsync(
      () => {
        const fullText = phrasesRef.current.join(" ").trim();
        setTranscript(fullText || null);
        if (!fullText) {
          setError("Could not recognize any speech. Please try again.");
        }
        setListening(false);
        recognizer.close();
        recognizerRef.current = null;
      },
      () => {
        setListening(false);
        recognizer.close();
        recognizerRef.current = null;
      }
    );
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript(null);
    setError(null);
    phrasesRef.current = [];
  }, []);

  return { listening, transcript, error, startListening, stopListening, clearTranscript };
}
