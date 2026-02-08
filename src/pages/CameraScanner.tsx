import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, X, RotateCcw, Check, Loader2, AlertTriangle, Info } from 'lucide-react';
import { toast } from 'sonner';
import type { Medicine } from '../types';

interface ScanResult extends Medicine {
  confidence: number;
  warnings?: string[];
}

export default function CameraScanner() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsStreaming(true);
      }
    } catch (err) {
      setError('Unable to access camera.');
      toast.error('Camera access denied');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (videoRef.current?.srcObject) {
      (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
      videoRef.current.srcObject = null;
      setIsStreaming(false);
    }
  }, []);

  const capturePhoto = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    setCapturedImage(canvas.toDataURL('image/jpeg', 0.8));
    stopCamera();
  }, [stopCamera]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setCapturedImage(ev.target?.result as string);
      setError(null);
    };
    reader.readAsDataURL(file);
  }, []);

  const analyzeMedicine = useCallback(async () => {
    if (!capturedImage) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      await new Promise(r => setTimeout(r, 1500));
      const demoResult: ScanResult = {
        name: 'Paracetamol 500mg',
        genericName: 'Acetaminofen',
        dosage: '500mg',
        type: 'tablet',
        description: 'Paracetamolul este un medicament folosit pentru ameliorarea durerii.',
        confidence: 0.85,
        warnings: ['Nu depășiți doza recomandată', 'Evitați consumul de alcool']
      };
      setResult(demoResult);
      toast.success('Medicine identified (Demo)');
    } catch (err) {
      setError('Analysis failed.');
      toast.error('Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  }, [capturedImage]);

  const retake = () => { setCapturedImage(null); setResult(null); setError(null); startCamera(); };

  return (
    <div className="min-h-screen bg-black relative">
      <div className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-b from-black/50 p-4 pt-8 flex items-center justify-between">
        <button onClick={() => navigate('/')} className="w-10 h-10 bg-black/30 backdrop-blur-sm rounded-full flex items-center justify-center"><X className="text-white" size={20} /></button>
        <h1 className="text-white font-semibold">Medicine Scanner</h1>
        <div className="w-10" />
      </div>

      {!capturedImage && !result && (
        <div className="relative w-full h-full">
          {isStreaming ? (
            <>
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-80 h-80 border-2 border-white/50 rounded-2xl relative">
                  <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-white rounded-tl-2xl"></div>
                  <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-white rounded-tr-2xl"></div>
                  <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-white rounded-bl-2xl"></div>
                  <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-white rounded-br-2xl"></div>
                </div>
              </div>
              <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
                <button onClick={capturePhoto} className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-lg active:scale-95 transition-transform"><div className="w-16 h-16 bg-white border-4 border-gray-300 rounded-full"></div></button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-white p-8">
              <Camera size={64} className="mb-6 text-gray-400" />
              <div className="space-y-4 w-full max-w-sm">
                <button onClick={startCamera} className="w-full bg-blue-600 py-4 rounded-xl font-semibold">Open Camera</button>
                <button onClick={() => fileInputRef.current?.click()} className="w-full bg-gray-700 py-4 rounded-xl font-semibold">Upload Photo</button>
              </div>
              {error && <p className="mt-6 text-red-400 text-sm">{error}</p>}
            </div>
          )}
        </div>
      )}

      {capturedImage && !result && (
        <div className="relative w-full h-full">
          <img src={capturedImage} alt="Captured" className="w-full h-full object-cover" />
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex space-x-4">
            <button onClick={retake} disabled={isAnalyzing} className="w-14 h-14 bg-gray-700/80 backdrop-blur-sm rounded-full flex items-center justify-center"><RotateCcw className="text-white" size={24} /></button>
            <button onClick={analyzeMedicine} disabled={isAnalyzing} className="w-14 h-14 bg-green-600 rounded-full flex items-center justify-center">
              {isAnalyzing ? <Loader2 className="animate-spin text-white" size={24} /> : <Check className="text-white" size={24} />}
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="bg-white min-h-screen pt-20">
          <div className="max-w-md mx-auto p-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4"><Check className="text-green-600" size={32} /></div>
              <h2 className="text-xl font-bold">Medicine Identified</h2>
              <p className="text-gray-500 text-sm">Confidence: {Math.round(result.confidence * 100)}%</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-6 mb-6">
              <h3 className="text-lg font-bold">{result.name}</h3>
              {result.genericName && <p className="text-gray-600 text-sm mb-2">Generic: {result.genericName}</p>}
              <div className="flex justify-between text-sm py-2 border-b"><span>Dosage</span><b>{result.dosage}</b></div>
              <div className="flex justify-between text-sm py-2 mb-4"><span>Type</span><b>{result.type}</b></div>
              {result.description && <p className="text-gray-600 text-xs leading-relaxed">{result.description}</p>}
            </div>
            {result.warnings?.length && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
                <div className="flex items-center mb-2 text-amber-800 font-semibold"><AlertTriangle size={18} className="mr-2" /> Warnings</div>
                {result.warnings.map((w, i) => <p key={i} className="text-amber-700 text-xs">• {w}</p>)}
              </div>
            )}
            <div className="space-y-3">
              <button onClick={() => navigate('/profile', { state: { medicineForSafetyCheck: result } })} className="w-full bg-red-600 text-white py-4 rounded-xl font-semibold">Check Safety</button>
              <button onClick={() => navigate('/cabinet', { state: { addMedicine: result } })} className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold">Add to Cabinet</button>
              <button onClick={retake} className="w-full bg-gray-200 text-gray-800 py-4 rounded-xl font-semibold">Scan Another</button>
            </div>
          </div>
        </div>
      )}
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
