/* ColdCall — the 206 real reefer trucks, as one InstancedMesh.

   Loads the same reefer-truck.glb the story page uses, merges its geometry
   into a single instanced draw call, and drives 206 instance matrices from
   the composition clock. Registers window.FleetTrucks, a plain custom
   element the animation mounts and seeks every frame. */

import * as THREE from 'three';
import { GLTFLoader } from './GLTFLoader.js';
import { mergeGeometries } from './BufferGeometryUtils.js';
import { RoomEnvironment } from './RoomEnvironment.js';

const INK = 0x201e1d, RED = 0xec3013, RELEASE = 0x0f9d74, HOLD = 0xe08a00;
const UNDECIDED = 0x8d949c;   // the livery stripe before a verdict exists

class FleetTrucks extends HTMLElement {
  connectedCallback() {
    if (this._up) return;
    this._up = true;
    // the host's inline style belongs to whoever mounted us (React owns
    // opacity + inset) — only fill in what is genuinely missing
    if (!this.style.position) this.style.position = 'absolute';
    this.style.display = 'block';

    const cv = document.createElement('canvas');
    cv.style.cssText = 'width:100%;height:100%;display:block';
    this.appendChild(cv);

    const r = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
    r.setPixelRatio(Math.min(devicePixelRatio, 2));
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.05;
    this._r = r;

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(r);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this._scene = scene;

    const cam = new THREE.PerspectiveCamera(38, 16 / 9, 0.5, 900);
    this._cam = cam;

    scene.add(new THREE.AmbientLight(0xffffff, 0.42));
    const key = new THREE.DirectionalLight(0xffffff, 1.15);
    key.position.set(70, 150, 90);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    const d = 260;
    key.shadow.camera.left = -d; key.shadow.camera.right = d;
    key.shadow.camera.top = d; key.shadow.camera.bottom = -d;
    key.shadow.camera.far = 700;
    key.shadow.bias = -0.0006;
    scene.add(key);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(2400, 2400),
      new THREE.ShadowMaterial({ opacity: 0.17 }));
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // ---- the road the opening runs on -----------------------------------
    // real geometry in world space: the truck drives through it, so the
    // motion is the truck's own, not a scrolled texture
    const road = new THREE.Group();
    road.visible = false;
    this._road = road;
    scene.add(road);

    const asphalt = new THREE.Mesh(
      new THREE.PlaneGeometry(520, 13),
      new THREE.MeshStandardMaterial({ color: 0x37342f, roughness: 0.92, metalness: 0 }));
    asphalt.rotation.x = -Math.PI / 2;
    asphalt.position.y = 0.02;
    asphalt.receiveShadow = true;
    road.add(asphalt);

    const dashGeo = new THREE.PlaneGeometry(3.4, 0.3);
    const dashMat = new THREE.MeshBasicMaterial({ color: 0xd8d2c4 });
    const dashes = new THREE.InstancedMesh(dashGeo, dashMat, 74);
    const dm = new THREE.Matrix4();
    for (let i = 0; i < 74; i++) {
      dm.makeRotationX(-Math.PI / 2);
      dm.setPosition(-256 + i * 7, 0.04, 0);
      dashes.setMatrixAt(i, dm);
    }
    road.add(dashes);

    const edgeMat = new THREE.MeshBasicMaterial({ color: 0x8d867a });
    [-6.2, 6.2].forEach(z => {
      const e = new THREE.Mesh(new THREE.PlaneGeometry(520, 0.22), edgeMat);
      e.rotation.x = -Math.PI / 2;
      e.position.set(0, 0.04, z);
      road.add(e);
    });

    this._ro = new ResizeObserver(() => this._size());
    this._ro.observe(this);
    this._size();
    this._load();
  }

  disconnectedCallback() { if (this._ro) this._ro.disconnect(); }

  _size() {
    const w = this.clientWidth || 1920, h = this.clientHeight || 1080;
    this._r.setSize(w, h, false);
    this._cam.aspect = w / h;
    this._cam.updateProjectionMatrix();
    this._draw();
  }

  async _load() {
    let src = null;
    try {
      src = (await new GLTFLoader().loadAsync('./vendor/models/reefer-truck.glb')).scene;
    } catch (e) { /* falls through to the box below */ }

    // ---- group the model's geometry by material role --------------------
    // the model is fully articulated (box, cab paint, chassis, chrome, tyres,
    // glass, lamps, reefer unit, livery stripe) — keep those roles apart
    // instead of merging them into one blob, so a truck reads as a truck.
    // Only the stripe carries the verdict; every other role is shared.
    const byRole = {};
    if (src) {
      src.updateMatrixWorld(true);
      src.traverse(o => {
        if (!o.isMesh) return;
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        const role = (mats[0] && mats[0].name) || 'body';
        const c = o.geometry.clone().applyMatrix4(o.matrixWorld);
        ['uv', 'uv1', 'color', 'tangent'].forEach(a => c.deleteAttribute(a));
        (byRole[role] = byRole[role] || { parts: [], color: mats[0] && mats[0].color })
          .parts.push(c.toNonIndexed());
      });
    }
    if (!Object.keys(byRole).length) {
      const b = new THREE.BoxGeometry(5.6, 2.7, 2.3);
      b.translate(0, 1.35, 0);
      byRole.boxWhite = { parts: [b.toNonIndexed()], color: new THREE.Color(0xf4f6f8) };
    }

    const roles = {};
    Object.entries(byRole).forEach(([k, v]) => {
      const g = v.parts.length > 1 ? mergeGeometries(v.parts, false) : v.parts[0];
      g.computeVertexNormals();
      roles[k] = { geo: g, color: v.color };
    });

    // one shared normalising transform over the whole model, so the roles
    // stay registered to each other
    const whole = new THREE.Box3();
    Object.values(roles).forEach(r => {
      r.geo.computeBoundingBox();
      whole.union(r.geo.boundingBox);
    });
    const sz = new THREE.Vector3();
    whole.getSize(sz);
    const s = 2.4 / Math.max(sz.x, 0.001);
    const fix = new THREE.Matrix4()
      .makeScale(s, s, s)
      .multiply(new THREE.Matrix4().makeTranslation(
        -(whole.min.x + whole.max.x) / 2, -whole.min.y, -(whole.min.z + whole.max.z) / 2));
    Object.values(roles).forEach(r => r.geo.applyMatrix4(fix));

    const TUNE = {
      cabPaint:  { roughness: 0.3,  metalness: 0.15, clearcoat: 1, clearcoatRoughness: 0.12 },
      boxWhite:  { roughness: 0.62, metalness: 0.02 },
      boxWall:   { roughness: 0.66, metalness: 0.02 },
      reefer:    { roughness: 0.5,  metalness: 0.25 },
      darkTrim:  { roughness: 0.55, metalness: 0.25 },
      chrome:    { roughness: 0.22, metalness: 0.95 },
      steel:     { roughness: 0.38, metalness: 0.85 },
      rubber:    { roughness: 0.95, metalness: 0 },
      glass:     { roughness: 0.08, metalness: 0.1, transparent: true, opacity: 0.62 },
      headlight: { roughness: 0.2, metalness: 0, emissive: 0xfff4d6, emissiveIntensity: 0.45 },
      taillight: { roughness: 0.3, metalness: 0, emissive: 0xb6312a, emissiveIntensity: 0.5 },
    };

    const N = window.FLEET_COUNTS || { release: 13, quarantine: 23, destroy: 170 };
    this._total = N.release + N.quarantine + N.destroy;
    this._shared = [];
    this._stripe = null;

    Object.entries(roles).forEach(([name, r]) => {
      if (name === 'stripe') return;   // per verdict, below
      const mat = new THREE.MeshPhysicalMaterial(Object.assign({
        color: r.color ? r.color.clone() : new THREE.Color(0xdddddd),
      }, TUNE[name] || { roughness: 0.6, metalness: 0.1 }));
      const im = new THREE.InstancedMesh(r.geo, mat, this._total);
      im.userData.role = name;
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      im.castShadow = name !== 'glass';
      im.frustumCulled = false;
      this._scene.add(im);
      this._shared.push(im);
    });

    // the verdict rides on the livery stripe and marker board only, and it is
    // NOT painted until the truck crosses the gate — one instanced mesh with
    // a per-instance colour, lerped from neutral to the verdict at the gate
    if (roles.stripe) {
      const im = new THREE.InstancedMesh(roles.stripe.geo, new THREE.MeshPhysicalMaterial({
        color: 0xffffff, roughness: 0.34, metalness: 0.1,
        clearcoat: 0.9, clearcoatRoughness: 0.2,
      }), this._total);
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      im.frustumCulled = false;
      const undecided = new THREE.Color(UNDECIDED);
      for (let i = 0; i < this._total; i++) im.setColorAt(i, undecided);
      this._scene.add(im);
      this._stripe = im;
      this._vcol = {
        release: new THREE.Color(RELEASE),
        quarantine: new THREE.Color(HOLD),
        destroy: new THREE.Color(RED),
      };
      this._undecided = undecided;
      this._tmpCol = new THREE.Color();
    }

    this._ready = true;
    if (src) this._buildHero(src, fix, roles);
    if (this._pending) this.seek(this._pending);
  }

  // ---- the hero truck: a real hierarchy, so its wheels can actually turn --
  // instancing shares one transform per truck, which cannot spin a wheel. For
  // the opening we show a single articulated clone instead, then hand off to
  // the instanced fleet once the camera is high enough that wheels no longer
  // read. Also lays roadside posts so the speed has something to measure on.
  _buildHero(src, fix, roles) {
    const hero = new THREE.Group();
    const inner = src.clone(true);
    hero.add(inner);
    hero.matrixAutoUpdate = true;
    // the same normalising transform the instanced roles got
    inner.applyMatrix4(fix);
    this._wheels = [];
    inner.traverse(o => {
      if (!o.isMesh) return;
      o.castShadow = true;
      const n = o.name || '';
      if (/^(tire|rim|hub)/.test(n)) {
        this._wheels.push({ mesh: o, base: o.rotation.y });
      }
      // give the hero the same tuned surfaces as the fleet
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const role = (mats[0] && mats[0].name) || '';
      const twin = this._shared.find(im => im.userData.role === role);
      if (twin) o.material = twin.material;
      if (role === 'stripe') { o.material = o.material.clone(); this._heroStripe = o.material; }
    });
    hero.visible = false;
    this._scene.add(hero);
    this._hero = hero;

    // roadside posts — static in world space, so the truck passing them is
    // what creates the sense of speed
    const postGeo = new THREE.BoxGeometry(0.16, 1.5, 0.16);
    postGeo.translate(0, 0.75, 0);
    const posts = new THREE.InstancedMesh(postGeo,
      new THREE.MeshStandardMaterial({ color: 0xb9b2a4, roughness: 0.85 }), 80);
    const pm = new THREE.Matrix4();
    for (let i = 0; i < 80; i++) {
      pm.identity().setPosition(-256 + Math.floor(i / 2) * 6.6, 0, (i % 2 ? 7.4 : -7.4));
      posts.setMatrixAt(i, pm);
    }
    posts.castShadow = true;
    posts.frustumCulled = false;
    this._road.add(posts);
  }

  /* the animation calls this every frame with the already-computed layout:
     { trucks: [{x, z, verdict, yaw, lift}], cam: {x, y, z, tx, ty, tz} } */
  seek(state) {
    if (!this._ready) { this._pending = state; return; }
    if (this._road) {
      const r = state.road;
      this._road.visible = !!r && r.op > 0.01;
      if (this._road.visible) {
        this._road.position.set(r.x, 0, r.z);
        this._road.children.forEach(c => {
          if (c.material && c.material.transparent !== undefined && !c.isInstancedMesh) {
            c.material.transparent = true;
            c.material.opacity = r.op;
          }
        });
      }
    }
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(),
          p = new THREE.Vector3(), sc = new THREE.Vector3(1, 1, 1);
    const e = new THREE.Euler();
    const sm = this._stripe;

    // ---- the hero truck for the road scene -------------------------------
    const h = state.hero;
    if (this._hero) {
      this._hero.visible = !!h && h.op > 0.01;
      if (this._hero.visible) {
        this._hero.position.set(h.x, 0, h.z);
        this._hero.rotation.set(h.pitch || 0, 0, h.roll || 0);
        // wheels turn by distance travelled, not by wall-clock time
        const spin = -(h.x - (h.x0 || 0)) / 0.2;
        this._wheels.forEach(w => { w.mesh.rotation.y = w.base + spin; });
        if (this._heroStripe) {
          this._heroStripe.color.copy(this._undecided);
        }
      }
    }
    state.trucks.forEach((t, gi) => {
      if (gi >= this._total) return;
      p.set(t.x, t.lift || 0, t.z);
      e.set(t.pitch || 0, t.yaw || 0, t.roll || 0);
      q.setFromEuler(e);
      m.compose(p, q, sc);
      this._shared.forEach(im => im.setMatrixAt(gi, m));
      if (sm) {
        sm.setMatrixAt(gi, m);
        // the stripe takes its verdict colour only as the truck is decided
        this._tmpCol.copy(this._undecided)
          .lerp(this._vcol[t.verdict] || this._undecided, t.decided || 0);
        sm.setColorAt(gi, this._tmpCol);
      }
    });
    this._shared.forEach(im => { im.instanceMatrix.needsUpdate = true; });
    if (sm) {
      sm.instanceMatrix.needsUpdate = true;
      if (sm.instanceColor) sm.instanceColor.needsUpdate = true;
    }
    const c = state.cam;
    this._cam.position.set(c.x, c.y, c.z);
    this._cam.lookAt(c.tx, c.ty, c.tz);
    this._draw();
  }

  _draw() { if (this._r && this._scene) this._r.render(this._scene, this._cam); }
}

customElements.define('fleet-trucks', FleetTrucks);
window.FleetTrucksReady = true;
