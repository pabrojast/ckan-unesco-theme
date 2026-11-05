// IHP-WINS edition: there is no Firebase project. The Firebase SDK imports resolve to shims/ (see vite.config.ts),
// which talk to the IHP-WINS (CKAN) community API with the visitor's IHP-WINS session.
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
export const configured = true;
export const app = initializeApp({});
export const auth = getAuth(app);
export const db = getFirestore(app);
/**
 * The platform administrators of the community (IHP-WINS sysadmins and the admins of the CKAN group) hold the
 * owner role that the Firebase version gave to one hard-coded email address.
 */
export const isPlatformOwner = (u: any): boolean => !!u && u.platformAdmin === true;
