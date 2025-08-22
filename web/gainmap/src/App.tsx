import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Canvas } from '@react-three/fiber'
import ImagePreview from './ImagePreview'
import { HDRJPGLoader } from '@monogrid/gainmap-js'
import { EXRLoader } from 'three/examples/jsm/loaders/EXRLoader'
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader'
import {
  Texture,
  WebGLRenderer,
  ACESFilmicToneMapping,
  DisplayP3ColorSpace
} from 'three'

const App = () => {
  const [file, setFile] = useState<File | null>(null)
  const [texture, setTexture] = useState<Texture | null>(null)
  const [previewTexture, setPreviewTexture] = useState<Texture | null>(null)
  const [exposure, setExposure] = useState(1)
  const [contrast, setContrast] = useState(1)
  const [saturation, setSaturation] = useState(1)
  const [isSdr, setIsSdr] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    setFile(file)

    const reader = new FileReader()
    reader.onload = () => {
      console.log('File loaded, creating texture...');
      const loader = file.name.endsWith('.exr')
        ? new EXRLoader()
        : new RGBELoader()

      loader.load(reader.result as string, (loadedTexture) => {
        console.log('Texture created from file.', loadedTexture);
        setTexture(loadedTexture)
        setPreviewTexture(loadedTexture);
      })
    }
    reader.readAsDataURL(file)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop })

  const handleSave = async () => {
    if (!file || !texture) return

    const renderer = new WebGLRenderer()
    const hdrJpg = new HDRJPGLoader(renderer)

    const result = await hdrJpg.encode(texture)

    const blob = new Blob([result.getSDRImage(), result.getGainMap()], { type: 'image/jpeg' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.name.replace(/\.[^/.]+$/, '') + '.jpg'
    link.click()
  }

  return (
    <div className="app">
      <div className="preview">
        {previewTexture && (
          <Canvas
            onCreated={({ gl }) => {
              gl.toneMapping = ACESFilmicToneMapping
              gl.toneMappingExposure = 1.0
              gl.outputColorSpace = DisplayP3ColorSpace
              gl.colorManagement = true
            }} >
            <ImagePreview
              key={previewTexture.uuid}
              texture={previewTexture}
              exposure={exposure}
              contrast={contrast}
              saturation={saturation}
              isSdr={isSdr}
              imageWidth={previewTexture.image.width}
              imageHeight={previewTexture.image.height}
            />
          </Canvas>
        )}
      </div>
      <div className="controls">
        <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
          <input {...getInputProps()} />
          {file ? (
            <p>{file.name}</p>
          ) : (
            <p>Drag 'n' drop some files here, or click to select files</p>
          )}
        </div>
        <div className="sliders">
          <label>
            Exposure: {exposure.toFixed(2)}
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={exposure}
              onChange={(e) => setExposure(parseFloat(e.target.value))}
            />
          </label>
          <label>
            Contrast: {contrast.toFixed(2)}
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={contrast}
              onChange={(e) => setContrast(parseFloat(e.target.value))}
            />
          </label>
          <label>
            Saturation: {saturation.toFixed(2)}
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={saturation}
              onChange={(e) => setSaturation(parseFloat(e.target.value))}
            />
          </label>
        </div>
        <div className="toggle">
          <label>
            <input
              type="checkbox"
              checked={isSdr}
              onChange={(e) => setIsSdr(e.target.checked)}
            />
            SDR Preview
          </label>
        </div>
        <button onClick={handleSave} disabled={!file}>
          Save JPG+Gainmap
        </button>
      </div>
    </div>
  )
}

export default App