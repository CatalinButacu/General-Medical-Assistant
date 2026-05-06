import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, X, RotateCcw, Check, Loader2, AlertTriangle, Info, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { scanMedicine } from '../services/api';
import type { Medicine, ScanMedicineMatch, ScanResponse } from '../types';

export default function CameraScanner() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [activeMatchIdx, setActiveMatchIdx] = useState(0);
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
      const scan = await scanMedicine(capturedImage);
      setResult(scan);
      setActiveMatchIdx(0);
      if (scan.matched) {
        toast.success(`Identificat: ${scan.matched.trade_name}`);
      } else if (scan.extracted.trade_name) {
        toast.warning(`Detectat ${scan.extracted.trade_name}, dar nu e în baza ANMDM`);
      } else {
        toast.error('Nu am putut identifica medicamentul. Reîncearcă cu o imagine mai clară.');
      }
    } catch (err: any) {
      setError(err?.message ?? 'Identificare eșuată.');
      toast.error('Identificare eșuată');
    } finally {
      setIsAnalyzing(false);
    }
  }, [capturedImage]);

  const navigateToCabinet = useCallback(() => {
    if (!result) return;
    const m: ScanMedicineMatch | null = result.candidates[activeMatchIdx] ?? result.matched;
    const e = result.extracted;
    const cabinetMedicine: Medicine & { expirationDate?: string } = m
      ? {
          name: m.trade_name,
          genericName: m.dci,
          dosage: m.concentration || e.dosage || '',
          type: (m.form || e.form || 'tablet').toLowerCase(),
          category: m.category,
          prescription_required: m.rx_status !== 'OTC',
          rx: m.rx_status !== 'OTC',
          symptoms: m.lay_symptoms,
          url: m.prospect_url,
          expirationDate: e.expiration_date ?? undefined,
        }
      : {
          name: e.trade_name ?? 'Medicament necunoscut',
          dosage: e.dosage ?? '',
          type: (e.form ?? 'tablet').toLowerCase(),
          expirationDate: e.expiration_date ?? undefined,
        };
    navigate('/cabinet', { state: { addMedicine: cabinetMedicine, fromScanner: true } });
  }, [navigate, result, activeMatchIdx]);

  const retake = () => { setCapturedImage(null); setResult(null); setActiveMatchIdx(0); setError(null); startCamera(); };
  const activeMatch: ScanMedicineMatch | null = result?.candidates[activeMatchIdx] ?? result?.matched ?? null;
  const alternatives: ScanMedicineMatch[] = (result?.candidates ?? []).filter((_, i) => i !== activeMatchIdx);

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
              <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${activeMatch ? 'bg-green-100' : 'bg-amber-100'}`}>
                {activeMatch
                  ? <Check className="text-green-600" size={32} />
                  : <Info className="text-amber-600" size={32} />}
              </div>
              <h2 className="text-xl font-bold">
                {activeMatch ? 'Medicament identificat' : 'Detectare parțială'}
              </h2>
              <p className="text-gray-500 text-xs mt-1">
                Încredere OCR: {Math.round(result.extracted.confidence * 100)}%
                {activeMatch && ` · potrivire ANMDM: ${activeMatch.match_score.toFixed(2)}`}
                {' · '}{result.latency_ms.toFixed(0)} ms
              </p>
            </div>

            {activeMatch && (
              <div className="bg-gray-50 rounded-xl p-6 mb-4">
                <h3 className="text-lg font-bold">{activeMatch.trade_name}</h3>
                <p className="text-gray-600 text-sm mb-3">
                  {activeMatch.dci} · <span className="font-mono text-xs">{activeMatch.atc_code}</span>
                </p>
                <div className="flex justify-between text-sm py-2 border-b"><span>Concentrație</span><b>{activeMatch.concentration || '—'}</b></div>
                <div className="flex justify-between text-sm py-2 border-b"><span>Formă</span><b className="capitalize">{activeMatch.form.toLowerCase()}</b></div>
                <div className="flex justify-between text-sm py-2 border-b"><span>Status</span>
                  <b className={activeMatch.rx_status === 'OTC' ? 'text-green-700' : 'text-red-700'}>
                    {activeMatch.rx_status === 'OTC' ? 'Fără rețetă' : activeMatch.rx_status}
                  </b>
                </div>
                {result.extracted.expiration_date && (
                  <div className="flex justify-between text-sm py-2 border-b">
                    <span>Expiră (din imagine)</span><b>{result.extracted.expiration_date}</b>
                  </div>
                )}
                {activeMatch.category && (
                  <p className="mt-3 text-blue-600 text-sm font-semibold">{activeMatch.category}</p>
                )}
              </div>
            )}

            {alternatives.length > 0 && (
              <div className="bg-white border border-gray-100 rounded-xl p-4 mb-4">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">
                  Alte potriviri posibile
                </div>
                <div className="space-y-2">
                  {alternatives.map(alt => {
                    const idx = result.candidates.indexOf(alt);
                    return (
                      <button
                        key={`${alt.trade_name}-${alt.atc_code}`}
                        onClick={() => setActiveMatchIdx(idx)}
                        className="w-full flex items-center justify-between bg-gray-50 hover:bg-blue-50 border border-gray-100 rounded-xl p-3 transition-colors text-left active:scale-[0.99]"
                      >
                        <div className="min-w-0">
                          <div className="font-bold text-sm text-gray-800 truncate">{alt.trade_name}</div>
                          <div className="text-[11px] text-gray-500 truncate">{alt.dci} · {alt.form.toLowerCase()} {alt.concentration}</div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                          <span className="text-[10px] font-mono text-gray-400">{alt.match_score.toFixed(2)}</span>
                          <ChevronRight size={14} className="text-gray-400" />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {!activeMatch && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
                <div className="flex items-center mb-3 text-amber-800 font-semibold"><AlertTriangle size={18} className="mr-2" /> Nu am găsit acest medicament în baza ANMDM</div>
                <div className="space-y-1.5 text-sm">
                  {result.extracted.trade_name && <div><span className="text-gray-500">Citit:</span> <b>{result.extracted.trade_name}</b></div>}
                  {result.extracted.dosage && <div><span className="text-gray-500">Doză:</span> <b>{result.extracted.dosage}</b></div>}
                  {result.extracted.form && <div><span className="text-gray-500">Formă:</span> <b className="capitalize">{result.extracted.form}</b></div>}
                  {result.extracted.expiration_date && <div><span className="text-gray-500">Expiră:</span> <b>{result.extracted.expiration_date}</b></div>}
                </div>
              </div>
            )}

            <div className="space-y-3">
              {activeMatch && (
                <button onClick={() => navigate('/profile', { state: { medicineForSafetyCheck: { name: activeMatch.trade_name, dosage: activeMatch.concentration, type: activeMatch.form } } })} className="w-full bg-red-600 text-white py-4 rounded-xl font-semibold">Verifică siguranța</button>
              )}
              <button onClick={navigateToCabinet} className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold">Adaugă în Cabinet</button>
              <button onClick={retake} className="w-full bg-gray-200 text-gray-800 py-4 rounded-xl font-semibold">Scanează altul</button>
            </div>
          </div>
        </div>
      )}
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
