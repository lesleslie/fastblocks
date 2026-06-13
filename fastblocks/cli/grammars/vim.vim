" Vim syntax file for FastBlocks templates
" Language: FastBlocks
" Maintainer: FastBlocks Team

if exists("b:current_syntax")
  finish
endif

" FastBlocks delimiters
syn region fastblocksVariable start="\[\[" end="\]\]" contains=fastblocksFilter,fastblocksString
syn region fastblocksBlock start="\[%" end="%\]" contains=fastblocksKeyword,fastblocksString
syn region fastblocksComment start="\[#" end="#\]"

" Keywords
syn keyword fastblocksKeyword if else elif endif for endfor block endblock extends include set macro endmacro

" Filters
syn match fastblocksFilter "|\s*\w\+" contained

" Strings
syn region fastblocksString start='"' end='"' contained
syn region fastblocksString start="'" end="'" contained

" Highlighting
hi def link fastblocksVariable Special
hi def link fastblocksBlock Keyword
hi def link fastblocksComment Comment
hi def link fastblocksKeyword Statement
hi def link fastblocksFilter Function
hi def link fastblocksString String

let b:current_syntax = "fastblocks"
