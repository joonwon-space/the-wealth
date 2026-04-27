import Image from "next/image";

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
  const lightClass = ["block dark:hidden", className].filter(Boolean).join(" ");
  const darkClass = ["hidden dark:block", className].filter(Boolean).join(" ");

  return (
    <>
      <Image
        src="/brand/logo-lockup.svg"
        alt="The Wealth"
        aria-label="The Wealth"
        width={width}
        height={height}
        priority={priority}
        className={lightClass}
      />
      <Image
        src="/brand/logo-lockup-dark.svg"
        alt=""
        aria-hidden
        width={width}
        height={height}
        priority={priority}
        className={darkClass}
      />
    </>
  );
}
