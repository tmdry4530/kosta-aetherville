# Data Model Contract

## Core entities

- `Citizen`: persona, position, animation, current action, relationships, plan tree, memory store reference
- `Memory`: observation/reflection/plan, importance, embedding pointer, access metadata
- `PlanTree`: day/hour/block decomposition with replan history
- `Vehicle`: kinematic state, path, passenger/destination, camera/Yolo detections
- `YoloDetection`: class, confidence, bbox, optional traffic light state, distance estimate
- `Location`: type, position, capacity, operating hours, metadata
- `TrafficLight`: controlled edges, state, remaining seconds, cycle pattern, RL control flag

## Implementation rules

- Python models live in `packages/shared-schemas/src/python/aetherville_schemas`.
- Generated TypeScript/Zod lives in `packages/shared-schemas/src/typescript`.
- IDs must be stable strings: `c01`, `v01`, `tl_01`, `cafe_01`.
- Position vectors use `[x, y, z]` in simulation coordinates.
- Browser coordinate conversion must live in `client/src/lib/coords.ts`.

## Required tests

- JSON fixture roundtrip for each entity.
- WebSocket state payload parse.
- REST citizen detail parse.
- God command parse.
- Backward-compatible optional fields for mock services.
