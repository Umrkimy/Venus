"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

// A counter that "New chat" bumps. The home page uses it as the chat card's
// key, so the card starts empty even when the page itself doesn't change.
const NewChatContext = createContext({ count: 0, startNewChat: () => {} });

export function NewChatProvider({ children }: { children: ReactNode }) {
  const [count, setCount] = useState(0);
  const startNewChat = () => setCount((old) => old + 1);
  return (
    <NewChatContext.Provider value={{ count, startNewChat }}>
      {children}
    </NewChatContext.Provider>
  );
}

export function useNewChat() {
  return useContext(NewChatContext);
}
