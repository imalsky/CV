%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Medium Length Professional CV - RESUME CLASS FILE
%
% This template has been downloaded from:
% http://www.LaTeXTemplates.com
%
% This class file defines the structure and design of the template. 
%
% Original header:
% Copyright (C) 2010 by Trey Hunner
%
% Copying and distribution of this file, with or without modification,
% are permitted in any medium without royalty provided the copyright
% notice and this notice are preserved. This file is offered as-is,
% without any warranty.
%
% Created by Trey Hunner and modified by www.LaTeXTemplates.com
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\ProvidesClass{cv}[2019/02/19 v1 cv]

\LoadClass[11pt,letterpaper]{article} % Font size and paper type
\usepackage[parfill]{parskip} % Remove paragraph indentation
\usepackage{array} % Required for boldface (\bf and \bfseries) tabular columns
\usepackage{ifthen} % Required for ifthenelse statements
\pagestyle{empty} % Suppress page numbers

%--------------------------------------------------------------------------
%	HEADINGS COMMANDS: Commands for printing name and address
%--------------------------------------------------------------------------

\def \name#1{\def\@name{#1}} % Defines the \name command to set name
\def \@name {} % Sets \@name to empty by default
\def  \phone#1{\def\@phone{#1}}
\def \@phone {}
\def  \email#1{\def\@email{#1}}
\def \@email {}

\let \@addressone \relax


% \address command can be used to set the first, second, and third address (last 2 optional)
\def \address #1{
     \def \@addressone {#1}
}

% \printsubhead is used to style an address line (given as input)
\def \printsubhead #1{
  \begingroup
    \def \\ {\addressSep\ }
    \centerline{#1}
    %\centerline{#2} | {#3}
  \endgroup
  \par
  \addressskip
}

% \printname is used to print the name as a page header
\def \printname {
  \begingroup
    %\hfil{\MakeUppercase{\namesize\bf \@name}}\hfil
    \hfil{{\namesize\bf \@name}}\hfil
    \nameskip\break
  \endgroup
}

%---------------------------------------------------------------------------
%	PRINT THE HEADING LINES
%--------------------------------------------------------------------------

\let\ori@document=\document
\renewcommand{\document}{
  \ori@document  % Begin document
  \printname % Print the name specified with \name
  \@ifundefined{@addressone}{}{ % Print the first address if specified
    \printsubhead{\@addressone}}
  \@ifundefined{@phone}{}{ % Print phone and email
    \printsubhead{\@phone $\ \|$ \@email}}
    
}

%----------------------------------------------------------------------------------------
%	SECTION FORMATTING
%----------------------------------------------------------------------------------------

% Defines the cSection environment for the large sections within the CV
\newenvironment{cSection}[1]{ % 1 input argument - section name
  %\sectionskip
  {\Large{\bf #1}\par}% Section title
  %\hrule % Horizontal line
    \vspace{-2em}
  \begin{list}{}{ % List for each individual item in the section
    \setlength{\leftmargin}{1.5em} % Margin within the section
    %\itemsep -0.5em \vspace{-0.5em} % Compress items in list together for aesthetics
  }
  \item[]
}{
  \end{list}
}

%----------------------------------------------------------------------------------------
%	WORK EXPERIENCE FORMATTING
%----------------------------------------------------------------------------------------

\newenvironment{cSubsection}[4]{ % 4 input arguments - company name, year(s) employed, job title and location
 {\bf #1} \hfill {#2} % Bold company name and date on the right
 \ifthenelse{\equal{#3}{}}{}{ % If the third argument is not specified, don't print the job title and location line
  \\
  {\em #3} \hfill {\em #4} % Italic job title and location
  %}\smallskip
  }
  %\begin{list}{$\cdot$}{\leftmargin=0em} % \cdot used for bullets, no indentation
  \begin{list}{}{\leftmargin=0em} % \cdot used for bullets, no indentation
   \itemsep -0.6em \vspace{-0.6em} % Compress items in list together for aesthetics
  }{
  \end{list}
  \vspace{0.4em} % Some space after the list of bullet points
}

% The below commands define the whitespace after certain things in the document - they can be \smallskip, \medskip or \bigskip
\def\namesize{\Large} % Size of the name at the top of the document
\def\addressskip{\smallskip} % The space between the two address (or phone/email) lines
\def\sectionlineskip{\smallskip} % The space above the horizontal line for each section 
\def\nameskip{\smallskip} % The space after your name at the top
\def\sectionskip{\smallskip} % The space after the heading section
