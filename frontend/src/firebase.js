import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyCtEGy6WiWVfhLwXXn4vj3gs-Er-Iz835E",
  authDomain: "ace1-a42fc.firebaseapp.com",
  projectId: "ace1-a42fc",
  storageBucket: "ace1-a42fc.firebasestorage.app",
  messagingSenderId: "779545135129",
  appId: "1:779545135129:web:784f63ab92ece43172c288",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);