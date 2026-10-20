"""Optional pygame view with fault-injection keys (python sim.py --ui)."""
import pygame

W, H = 980, 500
PX, X0, BELT_Y = 270, 70, 300            # pixels per metre, belt start, belt top
FAULT_KEYS = {pygame.K_e: "estop", pygame.K_o: "overload", pygame.K_j: "jam",
              pygame.K_c: "nocap", pygame.K_l: "leak", pygame.K_h: "hb_freeze",
              pygame.K_i: "infeed_empty", pygame.K_r: "runfb_loss"}
COMMAND_KEYS = {pygame.K_b: (2, 0), pygame.K_f: (4, 0), pygame.K_1: (1, 200), pygame.K_2: (1, 50),
                pygame.K_3: (1, 970), pygame.K_0: (3, 0)}
HELP = ["E e-stop   O overload   J jam   C no cap   L tank leak",
        "H freeze heartbeat   I infeed empty   R run-feedback loss",
        "B empty reject bin   F fill reject bin   1 / 2 / 3 tank to 20 / 5 / 97 %   0 clear faults"]
BG, BELT, INK, DIM = (245, 247, 250), (90, 98, 110), (30, 40, 55), (150, 158, 170)
GREEN, RED, AMBER, BLUE = (60, 160, 90), (200, 60, 60), (230, 160, 40), (70, 130, 200)


class View:
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Bottling line simulator")
        names = "dejavusansmono,consolas,menlo,monospace"
        self.font = pygame.font.SysFont(names, 14)
        self.small = pygame.font.SysFont(names, 12)

    def text(self, s, x, y, color=INK, font=None):
        self.screen.blit((font or self.font).render(s, True, color), (x, y))

    def update(self, plant, sensors, acts):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False
            if e.type == pygame.KEYDOWN:
                if e.key in FAULT_KEYS:
                    name = FAULT_KEYS[e.key]
                    plant.faults[name] = not plant.faults[name]
                elif e.key in COMMAND_KEYS:
                    plant.command(*COMMAND_KEYS[e.key])
        self.draw(plant, sensors, acts)
        pygame.display.flip()
        return True

    def draw(self, plant, sensors, acts):
        p, s = plant.p, self.screen
        s.fill(BG)
        # belt and stations
        belt_w = int(p.x_end * PX) + 40
        pygame.draw.rect(s, BELT, (X0 - 20, BELT_Y, belt_w, 14), border_radius=4)
        stations = [("FILL", p.x_fill, "I_FillPos"), ("CAP", p.x_cap, "I_CapPos"),
                    ("INSPECT", p.x_inspect, "I_InspectPos"), ("REJECT", p.x_reject, None),
                    ("OUTFEED", p.x_outfeed, "I_OutfeedSensor")]
        for name, x, tag in stations:
            cx = X0 + int(x * PX)
            pygame.draw.rect(s, DIM, (cx - int(p.window * PX), BELT_Y - 70,
                                      int(2 * p.window * PX), 70), 1)
            lamp = GREEN if tag and sensors[tag] else DIM
            pygame.draw.circle(s, lamp, (cx, BELT_Y - 86), 6)
            self.text(name, cx - 22, BELT_Y + 22, font=self.small)
        pygame.draw.rect(s, DIM, (X0 - 6, BELT_Y - 50, 12, 50), 1)
        self.text("GATE", X0 - 18, BELT_Y + 22, font=self.small)
        # valve jet, capper and pusher
        if acts.get("Q_FillValve"):
            pygame.draw.rect(s, BLUE, (X0 + int(p.x_fill * PX) - 2, BELT_Y - 150, 4, 90))
        if acts.get("Q_CapperRun"):
            pygame.draw.rect(s, AMBER, (X0 + int(p.x_cap * PX) - 14, BELT_Y - 100, 28, 10))
        px = X0 + int(p.x_reject * PX)
        ry = BELT_Y + 40 + int(40 * (1 - plant.pusher))
        pygame.draw.rect(s, RED, (px - 6, ry, 12, 40))
        # bottles
        for b in plant.bottles:
            bx = X0 + int(b.x * PX) - 11
            pygame.draw.rect(s, (225, 235, 245), (bx, BELT_Y - 46, 22, 46), border_radius=4)
            h = int(40 * min(1.0, b.fill_ml / p.bottle_capacity_ml))
            pygame.draw.rect(s, BLUE, (bx + 2, BELT_Y - 2 - h, 18, h))
            if b.capped:
                pygame.draw.rect(s, INK, (bx + 4, BELT_Y - 52, 14, 6))
        # tank
        pygame.draw.rect(s, DIM, (X0 + 30, 40, 90, 130), 2)
        h = int(126 * plant.level_pct / 100)
        pygame.draw.rect(s, BLUE, (X0 + 32, 40 + 128 - h, 86, h))
        self.text(f"TANK {plant.level_pct:5.1f} %", X0 + 20, 176)
        self.text(f"pump {acts.get('Q_PumpSpeed_raw', 0) / 327.67:5.1f} %", X0 + 20, 194)
        # readouts
        self.text(f"t = {plant.t:7.1f} s", 420, 40)
        self.text(f"belt {plant.speed:4.2f} m/s", 420, 60)
        self.text(f"reject bin {plant.bin_count}/{p.bin_capacity}", 420, 80)
        st = plant.stats
        self.text(f"released {st['released']}  rejected {st['rejected']}", 420, 100)
        for i, (tag, color) in enumerate([("Q_BeaconGreen", GREEN), ("Q_BeaconAmber", AMBER),
                                          ("Q_BeaconRed", RED)]):
            pygame.draw.circle(s, color if acts.get(tag) else DIM, (700 + i * 34, 52), 11)
        # faults and help
        self.text("ACTIVE FAULTS:", 420, 130)
        active = [n for n, v in plant.faults.items() if v]
        self.text(", ".join(active) if active else "none", 560, 130, RED if active else DIM)
        for i, line in enumerate(HELP):
            self.text(line, 30, 400 + i * 22, DIM, self.small)
