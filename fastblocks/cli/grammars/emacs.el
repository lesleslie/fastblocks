;;; fastblocks-mode.el --- Major mode for FastBlocks templates

(defvar fastblocks-mode-syntax-table
  (let ((table (make-syntax-table)))
    (modify-syntax-entry ?\" "\"" table)
    (modify-syntax-entry ?\' "\"" table)
    table)
  "Syntax table for `fastblocks-mode'.")

(defvar fastblocks-font-lock-keywords
  '(("\\[\\[.*?\\]\\]" . font-lock-variable-name-face)
    ("\\[%.*?%\\]" . font-lock-keyword-face)
    ("\\[#.*?#\\]" . font-lock-comment-face)
    ("\\b\\(if\\|else\\|elif\\|endif\\|for\\|endfor\\|block\\|endblock\\|extends\\|include\\|set\\|macro\\|endmacro\\)\\b" . font-lock-builtin-face))
  "Font lock keywords for FastBlocks mode.")

(define-derived-mode fastblocks-mode html-mode "FastBlocks"
  "Major mode for editing FastBlocks templates."
  (setq font-lock-defaults '(fastblocks-font-lock-keywords)))

(add-to-list 'auto-mode-alist '("\\.fb\\.html\\'" . fastblocks-mode))
(add-to-list 'auto-mode-alist '("\\.fastblocks\\'" . fastblocks-mode))

(provide 'fastblocks-mode)
;;; fastblocks-mode.el ends here
