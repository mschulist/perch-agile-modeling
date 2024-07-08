"use client";
import { getAuth, User } from "firebase/auth";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { getFirebaseConfig } from "@/firebase_config";

const { app, provider, db } = getFirebaseConfig();

/**
 * Renders the authentication component.
 *
 * @returns The rendered authentication component.
 */
export default function SignOut() {
  const [user, setUser] = useState<null | User>(null);

  const router = useRouter();

  const signOut = async () => {
    const auth = getAuth();
    try {
      await auth.signOut();
      setUser(null);
      router.push("/login");
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <button
      className="px-4 py-2 font-medium text-white bg-red-500 rounded-lg cursor-pointer hover:bg-red-600 transition-colors duration-300 ease-in-out"
      onClick={signOut}
    >
      Sign out
    </button>
  );
}
