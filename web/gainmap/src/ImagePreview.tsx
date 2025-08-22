
import { useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Environment } from '@react-three/drei'
import { Texture, ShaderMaterial } from 'three'

interface ImagePreviewProps {
  texture: Texture
  exposure: number
  contrast: number
  saturation: number
  isSdr: boolean
  imageWidth: number
  imageHeight: number
}

const ImagePreview = ({ texture, exposure, contrast, saturation, isSdr, imageWidth, imageHeight }: ImagePreviewProps) => {
  const materialRef = useRef<ShaderMaterial>(null!)
  const { viewport } = useThree();

  const shader = {
    uniforms: {
      map: { value: texture },
      exposure: { value: exposure },
      contrast: { value: contrast },
      saturation: { value: saturation },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D map;
      uniform float exposure;
      uniform float contrast;
      uniform float saturation;
      varying vec2 vUv;

      void main() {
        vec4 color = texture2D(map, vUv);
        color.rgb *= exposure;
        color.rgb = (color.rgb - 0.5) * contrast + 0.5;
        vec3 gray = vec3(dot(color.rgb, vec3(0.299, 0.587, 0.114)));
        color.rgb = mix(gray, color.rgb, saturation);
        gl_FragColor = color;
      }
    `,
  }

  useFrame(() => {
    if (materialRef.current) {
      materialRef.current.uniforms.exposure.value = exposure
      materialRef.current.uniforms.contrast.value = contrast
      materialRef.current.uniforms.saturation.value = saturation
    }
  })

  // Calculate aspect ratio and scale
  const aspect = imageWidth / imageHeight;
  const maxWidth = viewport.width * 0.9;
  const maxHeight = viewport.height * 0.9;

  let planeWidth = maxWidth;
  let planeHeight = planeWidth / aspect;

  if (planeHeight > maxHeight) {
    planeHeight = maxHeight;
    planeWidth = planeHeight * aspect;
  }


  return (
    <>
      <OrbitControls />
      <Environment preset="sunset" />
      <mesh scale={[planeWidth, planeHeight, 1]}>
        <planeGeometry args={[1, 1]} />
        <shaderMaterial
          ref={materialRef}
          args={[shader]}
          toneMapped={!isSdr}
        />
      </mesh>
    </>
  )
}

export default ImagePreview
