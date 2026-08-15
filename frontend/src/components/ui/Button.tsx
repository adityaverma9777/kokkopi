import * as React from "react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline'
  size?: 'sm' | 'md' | 'lg'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "primary", size = "md", ...props }, ref) => {
    
    let baseStyles = "inline-flex items-center justify-center font-bold transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-kokkopi-black disabled:opacity-50 disabled:pointer-events-none"
    
    const variants = {
      primary: "bg-kokkopi-black text-kokkopi-white border-brand shadow-brand hover:shadow-brand-hover",
      secondary: "bg-kokkopi-white text-kokkopi-black border-brand shadow-brand hover:shadow-brand-hover hover:bg-kokkopi-yellow",
      danger: "bg-kokkopi-red text-kokkopi-white border-brand shadow-brand hover:shadow-brand-hover",
      outline: "bg-transparent text-kokkopi-black border-brand hover:bg-kokkopi-yellow shadow-brand hover:shadow-brand-hover",
      ghost: "bg-transparent text-kokkopi-black hover:bg-kokkopi-white hover:border-brand",
    }

    const sizes = {
      sm: "h-9 px-4 text-sm",
      md: "h-11 px-6 text-base",
      lg: "h-14 px-8 text-lg",
    }

    const styles = `${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`

    return (
      <button ref={ref} className={styles} {...props} />
    )
  }
)
Button.displayName = "Button"
