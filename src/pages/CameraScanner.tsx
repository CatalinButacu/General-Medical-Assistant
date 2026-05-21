import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, X, RotateCcw, Check, Loader2, AlertTriangle, Info, ChevronRight, Image as ImageIcon, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { scanMedicine } from '../services/api';
import type { CabinetAddState, MedicineSafetyTarget, ScanMedicineMatch, ScanResponse } from '../types';

type CameraState = 'idle' | 'requesting' | 'live' | 'denied';

export default function CameraScanner() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [cameraState, setCameraState] = useState<CameraState>('idle');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [resolution, setResolution] = useState<{ w: number; h: number } | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [activeMatchIdx, setActiveMatchIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !stream) return;
    video.srcObject = stream;
    const handleMeta = () => setResolution({ w: video.videoWidth, h: video.videoHeight });
    video.addEventListener('loadedmetadata', handleMeta);
    return () => video.removeEventListener('loadedmetadata', handleMeta);
  }, [stream]);

  useEffect(() => () => stream?.getTracks().forEach(t => t.stop()), [stream]);

  const startCamera = useCallback(async () => {
    setError(null);
    setCameraState('requesting');
    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      setStream(newStream);
      setCameraState('live');
    } catch {
      setCameraState('denied');
      setError('Acces camera refuzat sau indisponibil. Folosește încărcarea din galerie.');
      toast.error('Acces camera refuzat');
    }
  }, []);

  const stopCamera = useCallback(() => {
    stream?.getTracks().forEach(t => t.stop());
    setStream(null);
    setResolution(null);
    setCameraState('idle');
  }, [stream]);

  const capturePhoto = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) {
      toast.error('Camera nu e gata, încearcă din nou.');
      return;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    setCapturedImage(canvas.toDataURL('image/jpeg', 0.85));
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Identificare eșuată.');
      toast.error('Identificare eșuată');
    } finally {
      setIsAnalyzing(false);
    }
  }, [capturedImage]);

  const navigateToCabinet = useCallback(() => {
    if (!result) return;
    const m: ScanMedicineMatch | null = result.candidates[activeMatchIdx] ?? result.matched;
    const e = result.extracted;
    const cabinetMedicine: CabinetAddState = m
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

  const retake = () => {
    setCapturedImage(null);
    setResult(null);
    setActiveMatchIdx(0);
    setError(null);
    startCamera();
  };

  const activeMatch: ScanMedicineMatch | null = result?.candidates[activeMatchIdx] ?? result?.matched ?? null;
  const alternatives: ScanMedicineMatch[] = (result?.candidates ?? []).filter((_, i) => i !== activeMatchIdx);

  const showCameraStage = !capturedImage && !result;

  return (
    <div className="min-h-screen bg-black relative">
      <div className="absolute top-0 left-0 right-0 z-30 bg-gradient-to-b from-black/70 to-transparent p-4 pt-8 flex items-center justify-between">
        <button
          onClick={() => { stopCamera(); navigate('/'); }}
          className="w-10 h-10 bg-black/40 backdrop-blur-sm rounded-full flex items-center justify-center active:scale-95 transition-transform"
          aria-label="Înapoi"
        >
          <X className="text-white" size={20} />
        </button>
        <h1 className="text-white font-semibold text-sm tracking-wide">Scaner medicamente</h1>
        <div className="w-10" />
      </div>

      {showCameraStage && (
        <div className="relative w-full h-screen overflow-hidden">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover transition-opacity duration-300 ${cameraState === 'live' ? 'opacity-100' : 'opacity-0'}`}
          />

          {cameraState === 'live' && (
            <>
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30" />
              </div>

              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-72 h-72 sm:w-80 sm:h-80 relative">
                  <CornerL position="tl" />
                  <CornerL position="tr" />
                  <CornerL position="bl" />
                  <CornerL position="br" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-white/70 text-[10px] font-bold uppercase tracking-[0.3em] bg-black/40 backdrop-blur-sm px-3 py-1.5 rounded-full">
                      Aliniază cutia
                    </div>
                  </div>
                </div>
              </div>

              <div className="absolute top-20 left-1/2 -translate-x-1/2 z-20">
                <div className="flex items-center gap-2 bg-black/50 backdrop-blur-md text-white text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-full">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                  </span>
                  Live · {resolution ? `${resolution.w}×${resolution.h}` : '—'}
                </div>
              </div>

              <div className="absolute bottom-0 left-0 right-0 z-20 pb-10 pt-6 px-6 flex items-center justify-between">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-12 h-12 bg-white/10 backdrop-blur-md rounded-2xl flex items-center justify-center active:scale-95 transition-transform"
                  aria-label="Încarcă din galerie"
                >
                  <ImageIcon className="text-white" size={20} />
                </button>
                <button
                  onClick={capturePhoto}
                  className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-2xl shadow-white/20 active:scale-90 transition-transform border-4 border-white/30"
                  aria-label="Captură"
                >
                  <div className="w-16 h-16 bg-white border-2 border-gray-200 rounded-full" />
                </button>
                <button
                  onClick={stopCamera}
                  className="w-12 h-12 bg-white/10 backdrop-blur-md rounded-2xl flex items-center justify-center active:scale-95 transition-transform"
                  aria-label="Oprește camera"
                >
                  <X className="text-white" size={20} />
                </button>
              </div>
            </>
          )}

          {cameraState === 'requesting' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
              <Loader2 size={48} className="animate-spin mb-4 text-blue-400" />
              <p className="text-sm font-medium">Pornesc camera…</p>
              <p className="text-xs text-gray-400 mt-1">Aprobă accesul când îți cere browserul</p>
            </div>
          )}

          {(cameraState === 'idle' || cameraState === 'denied') && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-8">
              <div className="w-20 h-20 bg-white/5 backdrop-blur-md rounded-3xl flex items-center justify-center mb-6 border border-white/10">
                <Camera size={36} className="text-white/80" />
              </div>
              <h2 className="text-lg font-bold mb-2">Scanează medicamentul</h2>
              <p className="text-sm text-gray-400 text-center mb-8 max-w-xs leading-relaxed">
                Fă o poză cutiei sau încarcă o imagine — recunoaștem numele și data de expirare.
              </p>
              <div className="space-y-3 w-full max-w-sm">
                <button
                  onClick={startCamera}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 py-4 rounded-2xl font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all active:scale-[0.98]"
                >
                  <Camera size={18} /> Deschide camera
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full flex items-center justify-center gap-2 bg-white/10 backdrop-blur-md py-4 rounded-2xl font-bold border border-white/10 hover:bg-white/15 transition-all active:scale-[0.98]"
                >
                  <ImageIcon size={18} /> Încarcă din galerie
                </button>
              </div>
              {error && (
                <div className="mt-6 flex items-start gap-2 text-red-300 text-xs max-w-sm">
                  <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{error}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {capturedImage && !result && (
        <div className="relative w-full h-screen">
          <img src={capturedImage} alt="Captured" className="w-full h-full object-contain bg-black" />
          <div className="absolute top-20 left-1/2 -translate-x-1/2 bg-black/50 backdrop-blur-md text-white text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-full flex items-center gap-2">
            <Zap size={10} className="text-amber-400" />
            {isAnalyzing ? 'Analizez imaginea…' : 'Confirmă imaginea'}
          </div>
          <div className="absolute bottom-0 left-0 right-0 pb-10 pt-6 px-6 flex justify-center items-center gap-4 bg-gradient-to-t from-black/80 to-transparent">
            <button
              onClick={retake}
              disabled={isAnalyzing}
              className="w-14 h-14 bg-white/15 backdrop-blur-md rounded-full flex items-center justify-center active:scale-95 transition-transform disabled:opacity-40"
              aria-label="Refă fotografia"
            >
              <RotateCcw className="text-white" size={22} />
            </button>
            <button
              onClick={analyzeMedicine}
              disabled={isAnalyzing}
              className="px-8 h-14 bg-green-600 rounded-full flex items-center gap-2 font-bold text-white shadow-2xl shadow-green-500/40 active:scale-95 transition-transform disabled:opacity-60"
            >
              {isAnalyzing
                ? <><Loader2 className="animate-spin" size={18} /> Identific…</>
                : <><Check size={18} /> Identifică medicament</>}
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
                {result.extracted.all_text && (
                  <details className="mt-3 pt-3 border-t border-amber-200">
                    <summary className="cursor-pointer text-[11px] font-bold text-amber-700 uppercase tracking-wider">
                      Text extras din imagine
                    </summary>
                    <pre className="mt-2 p-3 bg-white rounded-lg text-[11px] text-gray-700 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-64 overflow-y-auto">
                      {result.extracted.all_text}
                    </pre>
                  </details>
                )}
              </div>
            )}

            <div className="space-y-3">
              {activeMatch && (
                <button onClick={() => {
                  const target: MedicineSafetyTarget = {
                    name: activeMatch.trade_name,
                    dosage: activeMatch.concentration,
                    type: activeMatch.form,
                  };
                  navigate('/profile', { state: { medicineForSafetyCheck: target } });
                }} className="w-full bg-red-600 text-white py-4 rounded-xl font-semibold">Verifică siguranța</button>
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

function CornerL({ position }: { position: 'tl' | 'tr' | 'bl' | 'br' }) {
  const cls: Record<typeof position, string> = {
    tl: 'top-0 left-0 border-t-4 border-l-4 rounded-tl-2xl',
    tr: 'top-0 right-0 border-t-4 border-r-4 rounded-tr-2xl',
    bl: 'bottom-0 left-0 border-b-4 border-l-4 rounded-bl-2xl',
    br: 'bottom-0 right-0 border-b-4 border-r-4 rounded-br-2xl',
  };
  return <div className={`absolute w-10 h-10 border-white/90 ${cls[position]}`} />;
}
