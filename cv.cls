\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{cv}[2026/04/01 Minimal CV class for academic_cv.tex]

\LoadClass[11pt]{article}

\RequirePackage{enumitem}

\makeatletter
\newcommand{\@cvname}{}
\newcommand{\@cvphone}{}
\newcommand{\@cvemail}{}

\newcommand{\name}[1]{\gdef\@cvname{#1}}
\newcommand{\phone}[1]{\gdef\@cvphone{#1}}
\newcommand{\email}[1]{\gdef\@cvemail{#1}}

\AtBeginDocument{%
  \thispagestyle{fancy}%
  \begin{center}
    {\LARGE\bfseries \@cvname\par}
    \vspace{0.35em}
    {\normalsize
      \@cvphone%
      \ifx\@cvphone\@empty\else
        \ifx\@cvemail\@empty\else\enspace\textbar\enspace\fi
      \fi
      \@cvemail%
    \par}
  \end{center}
  \vspace{0.5em}
}

\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}

\newenvironment{cSection}[1]{%
  \par\vspace{0.8em}%
  {\large\bfseries #1\par}%
  \vspace{0.25em}%
  \hrule
  \vspace{0.45em}%
  \begin{itemize}[label={},leftmargin=0pt,itemsep=0.4em,parsep=0pt,topsep=0pt,partopsep=0pt]
}{%
  \end{itemize}%
}

\newenvironment{cSubsection}[4]{%
  \item
  \begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}p{0.72\textwidth}r}
    \textbf{#1} & #4 \\
    \textit{#2} & \textit{#3} \\
  \end{tabular*}
  \begin{itemize}[label={},leftmargin=1.2em,itemsep=0.15em,parsep=0pt,topsep=0.2em,partopsep=0pt]
}{%
  \end{itemize}%
}
\makeatother
