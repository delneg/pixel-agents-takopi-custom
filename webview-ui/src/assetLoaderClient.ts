/**
 * Client-side asset loading — replaces server-side PNG→SpriteData conversion.
 *
 * Uses canvas ImageData API to parse PNGs in the browser.
 * Only used in webapp mode — in VS Code extension mode, assets are sent via messages.
 */

import { setCharacterTemplates } from './office/sprites/spriteData.js'
import { setFloorSprites } from './office/floorTiles.js'
import { setWallSprites } from './office/wallTiles.js'

const PNG_ALPHA_THRESHOLD = 128

// Character sprite constants (from src/constants.ts)
const CHAR_COUNT = 6
const CHAR_FRAME_W = 16
const CHAR_FRAME_H = 32
const CHAR_FRAMES_PER_ROW = 7
const CHAR_DIRECTIONS = ['down', 'up', 'right'] as const

// Floor tile constants
const FLOOR_PATTERN_COUNT = 7
const FLOOR_TILE_SIZE = 16

// Wall tile constants
const WALL_PIECE_WIDTH = 16
const WALL_PIECE_HEIGHT = 32
const WALL_GRID_COLS = 4
const WALL_BITMASK_COUNT = 16

type SpriteData = string[][]

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error(`Failed to load image: ${url}`))
    img.src = url
  })
}

function getImageData(img: HTMLImageElement): ImageData {
  const canvas = document.createElement('canvas')
  canvas.width = img.width
  canvas.height = img.height
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(img, 0, 0)
  return ctx.getImageData(0, 0, img.width, img.height)
}

function rgbaToSpriteData(rgba: Uint8ClampedArray, w: number, h: number, stride: number, ox: number, oy: number): SpriteData {
  const sprite: SpriteData = []
  for (let y = 0; y < h; y++) {
    const row: string[] = []
    for (let x = 0; x < w; x++) {
      const idx = ((oy + y) * stride + (ox + x)) * 4
      const r = rgba[idx]
      const g = rgba[idx + 1]
      const b = rgba[idx + 2]
      const a = rgba[idx + 3]
      if (a < PNG_ALPHA_THRESHOLD) {
        row.push('')
      } else {
        row.push(`#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase())
      }
    }
    sprite.push(row)
  }
  return sprite
}

async function loadCharacterSprites(): Promise<void> {
  const characters: Array<{ down: SpriteData[]; up: SpriteData[]; right: SpriteData[] }> = []

  for (let ci = 0; ci < CHAR_COUNT; ci++) {
    try {
      const img = await loadImage(`./assets/characters/char_${ci}.png`)
      const imageData = getImageData(img)
      const rgba = imageData.data
      const stride = img.width

      const charData: { down: SpriteData[]; up: SpriteData[]; right: SpriteData[] } = { down: [], up: [], right: [] }

      for (let dirIdx = 0; dirIdx < CHAR_DIRECTIONS.length; dirIdx++) {
        const dir = CHAR_DIRECTIONS[dirIdx]
        const rowOffsetY = dirIdx * CHAR_FRAME_H
        const frames: SpriteData[] = []

        for (let f = 0; f < CHAR_FRAMES_PER_ROW; f++) {
          const frameOffsetX = f * CHAR_FRAME_W
          frames.push(rgbaToSpriteData(rgba, CHAR_FRAME_W, CHAR_FRAME_H, stride, frameOffsetX, rowOffsetY))
        }
        charData[dir] = frames
      }
      characters.push(charData)
    } catch (err) {
      console.warn(`Failed to load character sprite ${ci}:`, err)
      return // Can't proceed without all characters
    }
  }

  console.log(`[AssetLoader] Loaded ${characters.length} character sprites client-side`)
  setCharacterTemplates(characters)
}

async function loadFloorTiles(): Promise<void> {
  try {
    const img = await loadImage('./assets/floors.png')
    const imageData = getImageData(img)
    const rgba = imageData.data
    const stride = img.width

    const sprites: SpriteData[] = []
    for (let t = 0; t < FLOOR_PATTERN_COUNT; t++) {
      sprites.push(rgbaToSpriteData(rgba, FLOOR_TILE_SIZE, FLOOR_TILE_SIZE, stride, t * FLOOR_TILE_SIZE, 0))
    }

    console.log(`[AssetLoader] Loaded ${sprites.length} floor tile patterns client-side`)
    setFloorSprites(sprites)
  } catch (err) {
    console.warn('Failed to load floor tiles:', err)
  }
}

async function loadWallTiles(): Promise<void> {
  try {
    const img = await loadImage('./assets/walls.png')
    const imageData = getImageData(img)
    const rgba = imageData.data
    const stride = img.width

    const sprites: SpriteData[] = []
    for (let mask = 0; mask < WALL_BITMASK_COUNT; mask++) {
      const ox = (mask % WALL_GRID_COLS) * WALL_PIECE_WIDTH
      const oy = Math.floor(mask / WALL_GRID_COLS) * WALL_PIECE_HEIGHT
      sprites.push(rgbaToSpriteData(rgba, WALL_PIECE_WIDTH, WALL_PIECE_HEIGHT, stride, ox, oy))
    }

    console.log(`[AssetLoader] Loaded ${sprites.length} wall tile sprites client-side`)
    setWallSprites(sprites)
  } catch (err) {
    console.warn('Failed to load wall tiles:', err)
  }
}

/**
 * Load all pixel art assets client-side from static PNG files.
 * Called in webapp mode instead of receiving them via extension messages.
 */
export async function loadAllAssetsClientSide(): Promise<void> {
  // Load in the expected order: characters → floors → walls
  // (furniture is still sent from the server as JSON)
  await loadCharacterSprites()
  await loadFloorTiles()
  await loadWallTiles()
}
