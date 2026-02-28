import { useTheme } from "./ThemeProvider";
import { useEffect, useState, useRef, useMemo } from "react";

interface PreScaleLogoProps {
    size?: "sm" | "md" | "lg" | "hero";
    showWordmark?: boolean;
    animate?: boolean;
    preset?: "dense" | "balanced" | "minimal" | "blocks";
}

/* ASCII character density presets — dense to sparse */
const ASCII_PRESETS = {
    dense: " .,:;=+*#%@",
    balanced: " .-+*#",
    minimal: " .+#",
    blocks: " ░▒▓█",
};

/*
 * 3D ASCII art letters for "PreScale"
 * Each letter is an array of strings (rows).
 * Characters use density values 0-9 to represent brightness/depth.
 * These get mapped to the active preset at render time.
 */
const LETTER_DATA: Record<string, string[]> = {
    P: [
        "99999999000",
        "99000009900",
        "99000009900",
        "99999999000",
        "99000000000",
        "99000000000",
        "99000000000",
    ],
    r: [
        "00000000",
        "00000000",
        "98009990",
        "99900000",
        "99000000",
        "99000000",
        "99000000",
    ],
    e: [
        "00000000",
        "00000000",
        "09999900",
        "99000099",
        "99999999",
        "99000000",
        "09999900",
    ],
    S: [
        "09999990",
        "99000099",
        "99000000",
        "09999900",
        "00000099",
        "99000099",
        "09999900",
    ],
    c: [
        "00000000",
        "00000000",
        "09999900",
        "99000099",
        "99000000",
        "99000099",
        "09999900",
    ],
    a: [
        "00000000",
        "00000000",
        "09999900",
        "00000099",
        "09999999",
        "99000099",
        "09999999",
    ],
    l: [
        "990000",
        "990000",
        "990000",
        "990000",
        "990000",
        "990000",
        "099900",
    ],
    // e is reused
};

const WORD_LETTERS = ["P", "r", "e", "S", "c", "a", "l", "e"];

function mapToPreset(densityGrid: string[], presetChars: string): string[] {
    const maxIdx = presetChars.length - 1;
    return densityGrid.map((row) =>
        row
            .split("")
            .map((ch) => {
                const val = parseInt(ch, 10);
                if (isNaN(val) || val === 0) return " ";
                const idx = Math.round((val / 9) * maxIdx);
                return presetChars[idx] || " ";
            })
            .join("")
    );
}

export function PreScaleLogo({
    size = "sm",
    showWordmark = true,
    animate = true,
    preset = "dense",
}: PreScaleLogoProps) {
    const { theme } = useTheme();
    const [revealCol, setRevealCol] = useState(animate ? 0 : 999);
    const [glitchRow, setGlitchRow] = useState(-1);
    const hasAnimated = useRef(false);

    const presetChars = ASCII_PRESETS[preset];

    /* Build the full ASCII art word by combining letters side-by-side */
    const asciiLines = useMemo(() => {
        const rows = 7;
        const gap = size === "sm" ? 1 : 2;
        const lines: string[] = Array(rows).fill("");

        WORD_LETTERS.forEach((letter, li) => {
            const data = LETTER_DATA[letter];
            const mapped = mapToPreset(data, presetChars);
            for (let r = 0; r < rows; r++) {
                lines[r] += (li > 0 ? " ".repeat(gap) : "") + mapped[r];
            }
        });
        return lines;
    }, [presetChars, size]);

    const totalCols = asciiLines[0]?.length || 0;

    /* Animate: reveal columns left-to-right */
    useEffect(() => {
        if (!animate || hasAnimated.current) {
            setRevealCol(totalCols);
            return;
        }
        hasAnimated.current = true;
        let col = 0;
        const speed = Math.max(8, 400 / totalCols);
        const interval = setInterval(() => {
            col += 2;
            setRevealCol(col);
            if (col >= totalCols) clearInterval(interval);
        }, speed);
        return () => clearInterval(interval);
    }, [animate, totalCols]);

    /* Periodic glitch */
    useEffect(() => {
        if (!animate) return;
        const interval = setInterval(() => {
            setGlitchRow(Math.floor(Math.random() * 7));
            setTimeout(() => setGlitchRow(-1), 80);
        }, 4000);
        return () => clearInterval(interval);
    }, [animate]);

    const dims = {
        sm: { fontSize: 5, lineH: 1.1 },
        md: { fontSize: 8, lineH: 1.15 },
        lg: { fontSize: 12, lineH: 1.2 },
        hero: { fontSize: 16, lineH: 1.2 },
    }[size];

    const primaryColor = theme === "dark" ? "#a78bfa" : "#4f46e5";

    /* sm size in navbar — full ASCII PreScale at compact scale */
    if (size === "sm") {
        return (
            <div className="select-none">
                <pre
                    style={{
                        fontFamily: "'DM Mono', monospace",
                        fontSize: 3.4,
                        lineHeight: 1.15,
                        letterSpacing: "0.05em",
                        margin: 0,
                        padding: 0,
                        color: primaryColor,
                        whiteSpace: "pre",
                        overflow: "hidden",
                    }}
                >
                    {asciiLines.map((line, i) => {
                        const visible = line.slice(0, revealCol);
                        return (
                            <span
                                key={i}
                                style={{
                                    display: "block",
                                    opacity: glitchRow === i ? 0.3 : 1,
                                    transform: glitchRow === i ? "translateX(1px)" : "none",
                                }}
                            >
                                {visible}
                            </span>
                        );
                    })}
                </pre>
            </div>
        );
    }

    /* Larger sizes — full ASCII word */
    return (
        <div className="select-none">
            <pre
                style={{
                    fontFamily: "'DM Mono', monospace",
                    fontSize: dims.fontSize,
                    lineHeight: dims.lineH,
                    letterSpacing: "0.05em",
                    margin: 0,
                    padding: 0,
                    color: primaryColor,
                    whiteSpace: "pre",
                    overflow: "hidden",
                }}
            >
                {asciiLines.map((line, i) => {
                    const visible = line.slice(0, revealCol);
                    return (
                        <span
                            key={i}
                            style={{
                                display: "block",
                                opacity: glitchRow === i ? 0.3 : 1,
                                transform: glitchRow === i
                                    ? `translateX(${Math.random() > 0.5 ? 2 : -2}px)`
                                    : "none",
                                transition: "opacity 0.05s",
                            }}
                        >
                            {visible}
                        </span>
                    );
                })}
            </pre>
        </div>
    );
}
