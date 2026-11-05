// Type declarations for the IHP-WINS replacements of the Firebase SDK modules (shims/*.js).
// Loose on purpose: the app was written against the Firebase SDK and keeps its call shapes.

declare module "firebase/app" {
  export function initializeApp(options?: any): any;
  export function getApp(): any;
  export function getApps(): any[];
}

declare module "firebase/auth" {
  export type User = {
    uid: string;
    email: string | null;
    emailVerified: boolean;
    displayName: string | null;
    ckanName: string | null;
    platformAdmin: boolean;
    sysadmin: boolean;
    accountUrl: string | null;
    getIdToken(forceRefresh?: boolean): Promise<string>;
    reload(): Promise<void>;
  };
  export type Auth = { readonly currentUser: User | null; app: any; name: string };
  export function getAuth(app?: any): Auth;
  export function connectAuthEmulator(...args: any[]): void;
  export function onAuthStateChanged(auth: Auth, next: (user: User | null) => void, error?: (e: any) => void): () => void;
  export function signOut(auth: Auth): Promise<void>;
  export function reload(user: User): Promise<void>;
  export function signInWithEmailAndPassword(auth: Auth, email: string, password: string): Promise<any>;
  export function createUserWithEmailAndPassword(auth: Auth, email: string, password: string): Promise<any>;
  export function signInWithPopup(auth: Auth, provider: any): Promise<any>;
  export function signInWithRedirect(auth: Auth, provider: any): Promise<any>;
  export class GoogleAuthProvider { setCustomParameters(p: any): this; }
  export function sendPasswordResetEmail(auth: Auth, email: string, settings?: any): Promise<void>;
  export function verifyPasswordResetCode(auth: Auth, code: string): Promise<string>;
  export function confirmPasswordReset(auth: Auth, code: string, password: string): Promise<void>;
  export function checkActionCode(auth: Auth, code: string): Promise<any>;
  export function applyActionCode(auth: Auth, code: string): Promise<void>;
  export function loginUrl(): string;
  export function registerUrl(): string;
  export function logoutUrl(): string;
  export function resetUrl(): string;
}

declare module "firebase/firestore" {
  export class Timestamp {
    constructor(seconds: number, nanoseconds: number);
    readonly seconds: number;
    readonly nanoseconds: number;
    static fromMillis(ms: number): Timestamp;
    static fromDate(d: Date): Timestamp;
    static now(): Timestamp;
    toMillis(): number;
    toDate(): Date;
    isEqual(o: Timestamp): boolean;
  }
  export type DocumentData = { [field: string]: any };
  export type Firestore = any;
  export type DocumentReference<T = DocumentData> = { id: string; path: string; parent: any; firestore: any; type: "document" };
  export type CollectionReference<T = DocumentData> = Query<T> & { id: string; path: string; parent: any; type: "collection" };
  export type Query<T = DocumentData> = { firestore: any; type: string };
  export type DocumentSnapshot<T = DocumentData> = { id: string; ref: DocumentReference<T>; exists(): boolean; data(): any; get(field: string): any; metadata: any };
  export type QueryDocumentSnapshot<T = DocumentData> = DocumentSnapshot<T> & { data(): any };
  export type QuerySnapshot<T = DocumentData> = { docs: QueryDocumentSnapshot<T>[]; size: number; empty: boolean; forEach(cb: (d: QueryDocumentSnapshot<T>) => void): void; docChanges(): any[]; metadata: any };
  export type Unsubscribe = () => void;
  export type WriteBatch = { set(ref: any, data: any, options?: any): WriteBatch; update(ref: any, ...args: any[]): WriteBatch; delete(ref: any): WriteBatch; commit(): Promise<void> };
  export type Transaction = { get(ref: any): Promise<DocumentSnapshot>; set(ref: any, data: any, options?: any): Transaction; update(ref: any, ...args: any[]): Transaction; delete(ref: any): Transaction };
  export type QueryConstraint = any;
  export function getFirestore(app?: any): any;
  export function initializeFirestore(app?: any, settings?: any): any;
  export function connectFirestoreEmulator(...args: any[]): void;
  export function collection(parent: any, path: string, ...more: string[]): CollectionReference;
  export function doc(parent: any, path?: string, ...more: string[]): DocumentReference;
  export function query(base: any, ...constraints: any[]): Query;
  export function where(field: string, op: string, value: any): QueryConstraint;
  export function orderBy(field: string, direction?: "asc" | "desc"): QueryConstraint;
  export function limit(n: number): QueryConstraint;
  export function documentId(): string;
  export function getDoc(ref: DocumentReference): Promise<DocumentSnapshot>;
  export function getDocs(q: Query): Promise<QuerySnapshot>;
  export function getDocFromServer(ref: any): Promise<DocumentSnapshot>;
  export function getDocsFromServer(q: any): Promise<QuerySnapshot>;
  export function setDoc(ref: any, data: any, options?: any): Promise<void>;
  export function updateDoc(ref: any, ...args: any[]): Promise<void>;
  export function deleteDoc(ref: any): Promise<void>;
  export function addDoc(coll: any, data: any): Promise<DocumentReference>;
  export function writeBatch(db: any): WriteBatch;
  export function runTransaction<T>(db: any, fn: (tx: Transaction) => Promise<T>, options?: any): Promise<T>;
  export function onSnapshot(ref: DocumentReference, next: (snapshot: DocumentSnapshot) => void, error?: (e: any) => void): Unsubscribe;
  export function onSnapshot(ref: Query, next: (snapshot: QuerySnapshot) => void, error?: (e: any) => void): Unsubscribe;
  export function onSnapshot(ref: DocumentReference, observer: { next?: (snapshot: DocumentSnapshot) => void; error?: (e: any) => void }): Unsubscribe;
  export function onSnapshot(ref: Query, observer: { next?: (snapshot: QuerySnapshot) => void; error?: (e: any) => void }): Unsubscribe;
  export function serverTimestamp(): any;
  export function arrayUnion(...values: any[]): any;
  export function arrayRemove(...values: any[]): any;
  export function deleteField(): any;
  export function increment(n: number): any;
  export function createFirestore(transport: any): any;
}
