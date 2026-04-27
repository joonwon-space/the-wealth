"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useTheme } from "next-themes";

type BrandLogoVariant = "mark" | "lockup";

interface BrandLogoProps {
  variant?: BrandLogoVariant;
  size?: number;
  priority?: boolean;
  className?: string;
}

const MARK_DEFAULT_SIZE = 24;
const LOCKUP_DEFAULT_HEIGHT = 28;
const LOCKUP_ASPECT_RATIO = 6;

export function BrandLogo({
  variant = "mark",
  size,
  priority = false,
  className,
}: BrandLogoProps) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (variant === "mark") {
    const dimension = size ?? MARK_DEFAULT_SIZE;
    return (
      <Image
        src="/brand/logo-mark.svg"
        alt="The Wealth"
        aria-label="The Wealth"
        width={dimension}
        height={dimension}
        priority={priority}
        className={className}
      />
    );
  }

  const height = size ?? LOCKUP_DEFAULT_HEIGHT;
  const width = Math.round(height * LOCKUP_ASPECT_RATIO);
  const isDark = mounted && resolvedTheme === "dark";
  const src = isDark ? "/brand/logo-lockup-dark.svg" : "/brand/logo-lockup.svg";

  return (
    <Image
      src={src}
      alt="The Wealth"
      aria-label="The Wealth"
      width={width}
      height={height}
      priority={priority}
      className={className}
    />
  );
}
