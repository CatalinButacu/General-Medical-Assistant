import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getAnalytics } from 'firebase/analytics';

// Explicit configuration provided by user for test environment stability
const firebaseConfig = {
    apiKey: "AIzaSyDJQgQob-WmdkLQRXWJ9qBO7tZVO4_bOlI",
    authDomain: "rag-pharma.firebaseapp.com",
    projectId: "rag-pharma",
    storageBucket: "rag-pharma.firebasestorage.app",
    messagingSenderId: "166663531733",
    appId: "1:166663531733:web:ffa6fd640bf0a9e849865c",
    measurementId: "G-C4LWNWXQ3Y"
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const analytics = typeof window !== 'undefined' ? getAnalytics(app) : null;
