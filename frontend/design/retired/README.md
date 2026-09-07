# design/retired

Code kept out of the build for reference, not deleted.

`HeroScene.tsx.bak` was the WebGL hero: a react-three-fiber particle mesh. It
was replaced by `app/components/landing/HeroDrawing.tsx`, an axonometric section
in plain SVG. The mesh was decorative and generic, and it carried three.js and
react-three-fiber into the bundle to say nothing about construction chemistry.
Both packages were removed from package.json with it.
