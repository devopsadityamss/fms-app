import React from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function ConfirmDialog({ open, title, message, onConfirm, onCancel }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="bg-white p-6 rounded shadow w-full max-w-md"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "tween", duration: 0.2 }}
          >
            <h2 className="text-xl font-semibold mb-2">{title}</h2>
            <p className="text-slate-600 mb-4">{message}</p>

            <div className="flex justify-end gap-2">
              <button
                className="px-4 py-2 rounded border"
                onClick={onCancel}
              >
                Cancel
              </button>

              <button
                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700"
                onClick={onConfirm}
              >
                Delete
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
