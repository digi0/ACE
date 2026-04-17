const maskStyles = {
  'fade-edges':  { maskImage: 'radial-gradient(ellipse at center, black, transparent)' },
  'fade-center': { maskImage: 'radial-gradient(ellipse at center, transparent, black)' },
  'fade-top':    { maskImage: 'linear-gradient(to bottom, transparent, black)' },
  'fade-bottom': { maskImage: 'linear-gradient(to bottom, black, transparent)' },
  'fade-left':   { maskImage: 'linear-gradient(to right, transparent, black)' },
  'fade-right':  { maskImage: 'linear-gradient(to right, black, transparent)' },
  'fade-x':      { maskImage: 'linear-gradient(to right, transparent, black, transparent)' },
  'fade-y':      { maskImage: 'linear-gradient(to bottom, transparent, black, transparent)' },
  none: {},
};

function getBgImage(variant, fill, size) {
  switch (variant) {
    case 'dots':
      return `radial-gradient(${fill} 1px, transparent 1px)`;
    case 'grid':
      return `linear-gradient(to right, ${fill} 1px, transparent 1px), linear-gradient(to bottom, ${fill} 1px, transparent 1px)`;
    case 'diagonal-stripes':
      return `repeating-linear-gradient(45deg, ${fill}, ${fill} 1px, transparent 1px, transparent ${size}px)`;
    case 'horizontal-lines':
      return `linear-gradient(to bottom, ${fill} 1px, transparent 1px)`;
    case 'vertical-lines':
      return `linear-gradient(to right, ${fill} 1px, transparent 1px)`;
    case 'checkerboard':
      return `linear-gradient(45deg, ${fill} 25%, transparent 25%), linear-gradient(-45deg, ${fill} 25%, transparent 25%), linear-gradient(45deg, transparent 75%, ${fill} 75%), linear-gradient(-45deg, transparent 75%, ${fill} 75%)`;
    default:
      return undefined;
  }
}

export function BGPattern({
  variant = 'dots',
  mask = 'none',
  size = 24,
  fill = '#252525',
  style,
  ...props
}) {
  const bgSize = `${size}px ${size}px`;
  const backgroundImage = getBgImage(variant, fill, size);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        backgroundImage,
        backgroundSize: bgSize,
        ...(maskStyles[mask] || {}),
        ...style,
      }}
      {...props}
    />
  );
}
