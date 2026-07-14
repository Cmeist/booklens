"use client";

import { useCallback, useSyncExternalStore } from "react";

import {
  createEmptyProfile,
  loadUserProfile,
  saveUserProfile,
  USER_PROFILE_STORAGE_KEY,
  type UserProfile,
} from "@/lib/user-profile";

/** Stable empty profile for SSR — getServerSnapshot must return a cached value. */
const SERVER_PROFILE: UserProfile = createEmptyProfile();

let memoryProfile: UserProfile = SERVER_PROFILE;
let hasLoadedFromStorage = false;
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) {
    listener();
  }
}

function ensureLoaded(): UserProfile {
  if (!hasLoadedFromStorage && typeof window !== "undefined") {
    memoryProfile = loadUserProfile();
    hasLoadedFromStorage = true;
  }
  return memoryProfile;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getClientSnapshot(): UserProfile {
  return ensureLoaded();
}

function getServerSnapshot(): UserProfile {
  return SERVER_PROFILE;
}

function subscribeHydration(): () => void {
  return () => {};
}

function getHydratedClientSnapshot(): boolean {
  return true;
}

function getHydratedServerSnapshot(): boolean {
  return false;
}

function setProfileState(next: UserProfile) {
  const previous = memoryProfile;
  memoryProfile = next;
  hasLoadedFromStorage = true;
  try {
    saveUserProfile(next);
    emit();
  } catch (error) {
    memoryProfile = previous;
    throw error;
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (event: StorageEvent) => {
    if (event.key === USER_PROFILE_STORAGE_KEY) {
      memoryProfile = loadUserProfile();
      hasLoadedFromStorage = true;
      emit();
    }
  });
}

export function useUserProfile() {
  const hydrated = useSyncExternalStore(
    subscribeHydration,
    getHydratedClientSnapshot,
    getHydratedServerSnapshot,
  );
  const profile = useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);

  const setProfile = useCallback((next: UserProfile | ((current: UserProfile) => UserProfile)) => {
    const current = ensureLoaded();
    const resolved = typeof next === "function" ? next(current) : next;
    setProfileState(resolved);
  }, []);

  return { profile, setProfile, hydrated };
}
