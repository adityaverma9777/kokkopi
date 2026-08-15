import * as React from "react"

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'flat'
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = "", variant = "default", ...props }, ref) => {
    
    const baseStyles = "bg-kokkopi-white border-brand overflow-hidden p-6"
    
    const variants = {
      default: "shadow-brand",
      flat: "",
    }

    const styles = `${baseStyles} ${variants[variant]} ${className}`

    return (
      <div ref={ref} className={styles} {...props} />
    )
  }
)
Card.displayName = "Card"
