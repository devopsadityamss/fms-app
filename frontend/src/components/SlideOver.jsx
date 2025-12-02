import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FiX } from "react-icons/fi";

export default function SlideOver({ open, onClose, children, title = "" }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* BACKDROP */}
          <motion.div
            className="fixed inset-0 bg-black/30 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* PANEL */}
          <motion.div
            className="fixed right-0 top-0 h-full w-[380px] bg-white z-50 shadow-xl flex flex-col"
            initial={{ x: 400 }}
            animate={{ x: 0 }}
            exit={{ x: 400 }}
            transition={{ type: "tween", duration: 0.25 }}
          >
            {/* HEADER */}
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold text-lg">{title}</h2>
              <button
                onClick={onClose}
                className="p-2 hover:bg-slate-100 rounded"
              >
                <FiX size={18} />
              </button>
            </div>

            {/* BODY */}
            <div className="p-4 overflow-y-auto flex-1">{children}</div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
