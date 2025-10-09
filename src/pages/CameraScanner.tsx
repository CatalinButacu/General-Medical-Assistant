import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, X, RotateCcw, Check, Loader2, AlertTriangle, Info } from 'lucide-react';
import { toast } from 'sonner';

interface MedicineResult {
  id: string;
  name: string;
  genericName: string;
  dosage: string;
  type: string;
  description: string;
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
  const [medicineResult, setMedicineResult] = useState<MedicineResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Use back camera on mobile
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsStreaming(true);
      }
    } catch (err) {
      console.error('Error accessing camera:', err);
      setError('Unable to access camera. Please check permissions.');
      toast.error('Camera access denied');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
      setIsStreaming(false);
    }
  }, []);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    if (!context) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);

    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    setCapturedImage(imageData);
    stopCamera();
  }, [stopCamera]);

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setCapturedImage(result);
      setError(null);
    };
    reader.readAsDataURL(file);
  }, []);

  const analyzeMedicine = useCallback(async () => {
    if (!capturedImage) return;

    setIsAnalyzing(true);
    setError(null);
    setMedicineResult(null);

    try {
      // Convert base64 to blob
      const response = await fetch(capturedImage);
      const blob = await response.blob();
      
      const formData = new FormData();
      formData.append('image', blob, 'medicine.jpg');

      const apiResponse = await fetch('/api/medicine/identify', {
        method: 'POST',
        body: formData,
      });

      if (!apiResponse.ok) {
        throw new Error('Failed to analyze medicine');
      }

      const result = await apiResponse.json();
      
      if (result.success && result.medicine) {
        setMedicineResult(result.medicine);
        toast.success('Medicine identified successfully!');
      } else {
        setError(result.message || 'Could not identify the medicine');
        toast.error('Medicine not recognized');
      }
    } catch (err) {
      console.error('Error analyzing medicine:', err);
      setError('Failed to analyze the image. Please try again.');
      toast.error('Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  }, [capturedImage]);

  const retakePhoto = useCallback(() => {
    setCapturedImage(null);
    setMedicineResult(null);
    setError(null);
    startCamera();
  }, [startCamera]);

  const handleSafetyCheck = useCallback(() => {
    if (medicineResult) {
      // Navigate to safety check with medicine data
      navigate('/profile', { 
        state: { 
          medicineForSafetyCheck: medicineResult 
        } 
      });
    }
  }, [medicineResult, navigate]);

  return (
    <div className="min-h-screen bg-black relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-b from-black/50 to-transparent">
        <div className="flex items-center justify-between p-4 pt-8">
          <button
            onClick={() => navigate('/')}
            className="w-10 h-10 bg-black/30 backdrop-blur-sm rounded-full flex items-center justify-center"
          >
            <X className="text-white" size={20} />
          </button>
          <h1 className="text-white font-semibold">Medicine Scanner</h1>
          <div className="w-10 h-10" /> {/* Spacer */}
        </div>
      </div>

      {/* Camera View */}
      {!capturedImage && !medicineResult && (
        <div className="relative w-full h-full">
          {isStreaming ? (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
              
              {/* Scan Frame Overlay */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-80 h-80 border-2 border-white/50 rounded-2xl relative">
                  <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-white rounded-tl-2xl"></div>
                  <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-white rounded-tr-2xl"></div>
                  <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-white rounded-bl-2xl"></div>
                  <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-white rounded-br-2xl"></div>
                  <div className="absolute -bottom-12 left-1/2 transform -translate-x-1/2">
                    <p className="text-white text-sm text-center">
                      Position medicine within the frame
                    </p>
                  </div>
                </div>
              </div>

              {/* Capture Button */}
              <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2">
                <button
                  onClick={capturePhoto}
                  className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-lg active:scale-95 transition-transform"
                >
                  <div className="w-16 h-16 bg-white border-4 border-gray-300 rounded-full"></div>
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-white p-8">
              <Camera size={64} className="mb-6 text-gray-400" />
              <h2 className="text-xl font-semibold mb-4">Ready to Scan</h2>
              <p className="text-gray-300 text-center mb-8">
                Take a clear photo of your medicine for instant identification
              </p>
              
              <div className="space-y-4 w-full max-w-sm">
                <button
                  onClick={startCamera}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 px-6 rounded-xl font-semibold transition-colors"
                >
                  Open Camera
                </button>
                
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full bg-gray-700 hover:bg-gray-600 text-white py-4 px-6 rounded-xl font-semibold transition-colors"
                >
                  Upload Photo
                </button>
              </div>

              {error && (
                <div className="mt-6 bg-red-500/20 border border-red-500/30 rounded-lg p-4 max-w-sm">
                  <div className="flex items-center">
                    <AlertTriangle className="text-red-400 mr-2" size={20} />
                    <p className="text-red-300 text-sm">{error}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Captured Image Review */}
      {capturedImage && !medicineResult && (
        <div className="relative w-full h-full">
          <img
            src={capturedImage}
            alt="Captured medicine"
            className="w-full h-full object-cover"
          />
          
          {/* Action Buttons */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex space-x-4">
            <button
              onClick={retakePhoto}
              disabled={isAnalyzing}
              className="w-14 h-14 bg-gray-700/80 backdrop-blur-sm rounded-full flex items-center justify-center disabled:opacity-50"
            >
              <RotateCcw className="text-white" size={24} />
            </button>
            
            <button
              onClick={analyzeMedicine}
              disabled={isAnalyzing}
              className="w-14 h-14 bg-green-600 rounded-full flex items-center justify-center disabled:opacity-50"
            >
              {isAnalyzing ? (
                <Loader2 className="text-white animate-spin" size={24} />
              ) : (
                <Check className="text-white" size={24} />
              )}
            </button>
          </div>

          {isAnalyzing && (
            <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
              <div className="bg-white rounded-xl p-6 text-center">
                <Loader2 className="animate-spin mx-auto mb-4 text-blue-600" size={32} />
                <p className="text-gray-800 font-semibold">Analyzing medicine...</p>
                <p className="text-gray-600 text-sm mt-1">This may take a few seconds</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Medicine Result */}
      {medicineResult && (
        <div className="bg-white min-h-screen">
          <div className="max-w-md mx-auto p-4">
            {/* Result Header */}
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="text-green-600" size={32} />
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">Medicine Identified</h2>
              <p className="text-gray-600">Confidence: {Math.round(medicineResult.confidence * 100)}%</p>
            </div>

            {/* Medicine Details */}
            <div className="bg-gray-50 rounded-xl p-6 mb-6">
              <h3 className="text-lg font-bold text-gray-800 mb-2">{medicineResult.name}</h3>
              {medicineResult.genericName && (
                <p className="text-gray-600 mb-2">Generic: {medicineResult.genericName}</p>
              )}
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-gray-500">Dosage</span>
                <span className="font-semibold text-gray-800">{medicineResult.dosage}</span>
              </div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-gray-500">Type</span>
                <span className="font-semibold text-gray-800">{medicineResult.type}</span>
              </div>
              {medicineResult.description && (
                <div>
                  <h4 className="font-semibold text-gray-800 mb-2">Description</h4>
                  <p className="text-gray-600 text-sm leading-relaxed">{medicineResult.description}</p>
                </div>
              )}
            </div>

            {/* Warnings */}
            {medicineResult.warnings && medicineResult.warnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
                <div className="flex items-center mb-2">
                  <AlertTriangle className="text-amber-600 mr-2" size={20} />
                  <h4 className="font-semibold text-amber-800">Important Warnings</h4>
                </div>
                <ul className="space-y-1">
                  {medicineResult.warnings.map((warning, index) => (
                    <li key={index} className="text-amber-700 text-sm">• {warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-3">
              <button
                onClick={handleSafetyCheck}
                className="w-full bg-red-600 hover:bg-red-700 text-white py-4 px-6 rounded-xl font-semibold transition-colors"
              >
                Check Safety for Me
              </button>
              
              <button
                onClick={() => navigate('/cabinet', { state: { addMedicine: medicineResult } })}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 px-6 rounded-xl font-semibold transition-colors"
              >
                Add to Medicine Cabinet
              </button>
              
              <button
                onClick={retakePhoto}
                className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 py-4 px-6 rounded-xl font-semibold transition-colors"
              >
                Scan Another Medicine
              </button>
            </div>

            {/* Info Note */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start">
                <Info className="text-blue-600 mr-2 mt-0.5" size={16} />
                <p className="text-blue-700 text-xs">
                  This identification is for informational purposes only. Always verify with a healthcare professional before taking any medication.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        className="hidden"
      />

      {/* Hidden canvas for image capture */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}