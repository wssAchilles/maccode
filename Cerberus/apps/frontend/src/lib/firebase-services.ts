import { getAuth } from "firebase/auth"
import { getFirestore } from "firebase/firestore"
import { getFunctions } from "firebase/functions"
import { getStorage } from "firebase/storage"

import { initFirebase } from "./firebase"

export function getFirebaseServices() {
  const app = initFirebase()
  if (!app) {
    return null
  }

  return {
    app,
    auth: getAuth(app),
    firestore: getFirestore(app),
    storage: getStorage(app),
    functions: getFunctions(app),
  }
}

