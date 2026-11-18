import { createContext, useCallback, useContext, useState } from "react";
import Icon from "./Icon";
import { traduire, useLangue } from "../contexte/LangueContext";

const ToastContext = createContext(() => {});

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const { langue } = useLangue();
  const notifier = useCallback((message, type = "success") => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((items) => [...items, { id, message, type }]);
    window.setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 4000);
  }, []);
  return (
    <ToastContext.Provider value={notifier}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => <div key={toast.id} className={`toast toast-${toast.type}`} role="status"><Icon name={toast.type === "error" ? "info" : "check"} size={18}/><span>{traduire(toast.message, langue)}</span></div>)}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() { return useContext(ToastContext); }
