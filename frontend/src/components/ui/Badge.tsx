import * as React from "react"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
}

export function Badge({ className = "", variant = "default", ...props }: BadgeProps) {
  
  const baseStyles = "inline-flex items-center border-brand px-2.5 py-0.5 text-xs font-bold font-mono uppercase tracking-widest transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
  
  const variants = {
    default: "bg-kokkopi-black text-kokkopi-white",
    success: "bg-kokkopi-teal text-kokkopi-white",
    warning: "bg-kokkopi-yellow text-kokkopi-black",
    danger: "bg-kokkopi-red text-kokkopi-white",
    info: "bg-kokkopi-blue text-kokkopi-white",
  }

  const styles = `${baseStyles} ${variants[variant]} ${className}`

  return (
    <div className={styles} {...props} />
  )
}
