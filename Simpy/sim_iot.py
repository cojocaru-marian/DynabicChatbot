# https://realpython.com/simpy-simulating-with-python/
import time

import simpy
import random
import statistics
import ipaddress
import random
from typing import Dict, List, Tuple, Union
from ipaddress import IPv4Network

################ GENERATOR FUNCTIONS #################
MAX_IPV4 = ipaddress.IPv4Address._ALL_ONES  # 2 ** 32 - 1
MAX_IPV6 = ipaddress.IPv6Address._ALL_ONES  # 2 ** 128 - 1


def random_ipv4():
    return ipaddress.IPv4Address._string_from_ip_int(
        random.randint(0, MAX_IPV4)
    )


class Loc:
    def __init__(self, long, lat):
        self.long = long
        self.lat = lat


def generate_random_LocData(lat, lon, num_rows) -> List[Loc]:
    res = []
    for _ in range(num_rows):
        hex1 = '%012x' % random.randrange(16 ** 12)  # 12 char random string
        flt = float(random.randint(0, 100))
        dec_lat = random.random() / 100
        dec_lon = random.random() / 100
        res.append(Loc(lon + dec_lon, lat + dec_lat))
    return res


def generate_random_ipAddresses(num: int) -> List[str]:
    return [random_ipv4() for _ in range(num)]


allDevices = []
allDevicesByHouse = {}

#################################


import random
import sys
import math


class IoTDevice(object):
    def __init__(self, env: simpy.Environment, IP: str, Port: int, ParentHub, id: str, loc_lat, loc_long) -> None:
        self.env = env
        self.IP = IP
        self.Port = Port
        self.hub = ParentHub
        self.id = id
        self.loc_lat = loc_lat
        self.loc_long = loc_long

        self.duration_between_metrics_update = None
        self.last_metrics_update_time = 0

    def start(self):
        self.action = self.env.process(self.run())

    def run(self):
        while True:
            # First try to log on the action made
            cycle_start_time = self.env.now

            next_metrics_update = self.last_metrics_update_time + self.duration_between_metrics_update
            if next_metrics_update > cycle_start_time:
                yield self.env.timeout(next_metrics_update - cycle_start_time)
            cycle_start_time = self.env.now

            print(f"device: {self.id} starting to log at {cycle_start_time}")
            with self.hub.loggers.request() as request:
                yield request
                yield self.env.process(self.hub.log_action(self))

            print(f"device: {self.id} starting to update metrics at {self.env.now}")
            self.last_metrics_update_time = self.env.now
            # Then try to update the metrics
            with self.hub.metrics.request() as request:
                yield request
                yield self.env.process(self.hub.update_metrics_in_database(self))
            print(f"device: {self.id} ended to update metrics at {self.env.now}")


class IoTDeviceSmartTV(IoTDevice):
    def __init__(self, env: simpy.Environment, IP: str, Port: int, ParentHub, id: str, loc_lat, loc_long):
        super().__init__(env, IP, Port, ParentHub, id, loc_lat, loc_long)
        self.duration_between_metrics_update = 400


class IoTDeviceSmartKettle(IoTDevice):
    def __init__(self, env: simpy.Environment, IP: str, Port: int, ParentHub, id: str, loc_lat, loc_long):
        super().__init__(env, IP, Port, ParentHub, id, loc_lat, loc_long)
        self.duration_between_metrics_update = 500


class IoTDeviceSmartBrush(IoTDevice):
    def __init__(self, env: simpy.Environment, IP: str, Port: int, ParentHub, id: str, loc_lat, loc_long):
        super().__init__(env, IP, Port, ParentHub, id, loc_lat, loc_long)
        self.duration_between_metrics_update = 2000


class IoTDeviceSmartFlower(IoTDevice):
    def __init__(self, env: simpy.Environment, IP: str, Port: int, ParentHub, id: str, loc_lat, loc_long):
        super().__init__(env, IP, Port, ParentHub, id, loc_lat, loc_long)
        self.duration_between_metrics_update = 2000


class IoTDeviceSmartWindow(IoTDevice):
    def __init__(self, env: simpy.Environment, IP: str, Port: int, ParentHub, id: str, loc_lat, loc_long):
        super().__init__(env, IP, Port, ParentHub, id, loc_lat, loc_long)
        self.duration_between_metrics_update = 1000


# The IoT hub has 3 types of processes, each with different hardware process:
# a) a logger
# b) a metrics storer (e.g., flower temperature at every minute, etc)
# c) a rules processors - reads the metrics and take actions according to some predefined rules
class IoTHub(object):
    time_between_updaterules = 1000.0  # 3 seconds between updates

    # The parameters represent the number of parallel processes that are able to run for different operations
    def __init__(self, env, num_loggers: int, num_store_metrics: int, num_rules_processors: int):
        self.env = env
        self.loggers = simpy.Resource(env, num_loggers)
        self.metrics = simpy.Resource(env, num_store_metrics)
        self.rules = simpy.Resource(env, num_rules_processors)

        self.last_time_rules_checked = 0.0
        self.action = None

    def start(self):
        self.action = self.env.process(self.run())

    def log_action(self, entity: IoTDevice):
        print(f"Logging state for entity: {entity.id}")
        yield self.env.timeout(random.uniform(30, 60))

    def update_metrics_in_database(self, entity: IoTDevice):
        print(f"Updating metrics for entity: {entity.id}")
        yield self.env.timeout(random.uniform(30, 120))

    def check_update_rules(self) -> bool:
        print(f"Hub updating rules starting at {self.env.now}...")
        self.last_time_rules_checked = self.env.now
        yield self.env.timeout(random.uniform(100, 200))
        return True
        # TODO: this should action back on devices !

    def run(self):
        def getTimeToNextRuleCheck() -> float:
            return (IoTHub.time_between_updaterules + self.last_time_rules_checked) - self.env.now

        while True:
            time_up_to_next_rule_check = getTimeToNextRuleCheck()

            if time_up_to_next_rule_check > 0:
                yield self.env.timeout(time_up_to_next_rule_check)

            assert getTimeToNextRuleCheck() <= 0, "it should have slept.."
            with self.rules.request() as request:
                yield request
                yield self.env.process(self.check_update_rules())

            print(f"Finished rules check: at {self.env.now}")


def generateRandomDeployment(env: simpy.Environment,
                             globalHub: IoTHub,
                             nhouses: int,
                             center_lat: str,
                             center_long: str):
    locations = generate_random_LocData(center_lat, center_long, nhouses)
    baseIpAddresses = generate_random_ipAddresses(nhouses)
    fixedPort = 5776

    # Generate each device type for each home
    for houseIndex in range(nhouses):
        loc = locations[houseIndex].lat
        long = locations[houseIndex].long

        network = IPv4Network(baseIpAddresses[houseIndex])
        hosts_iterator = (host for host in network.hosts())

        ips = generate_random_ipAddresses(5)

        tv = IoTDeviceSmartTV(env, ips[0], fixedPort, globalHub, f"{houseIndex}_tv", loc, long)
        brush = IoTDeviceSmartBrush(env, ips[1], fixedPort, globalHub, f"{houseIndex}_brush", loc, long)
        window = IoTDeviceSmartWindow(env, ips[2], fixedPort, globalHub, f"{houseIndex}_window", loc,
                                      long)
        flower = IoTDeviceSmartFlower(env, ips[3], fixedPort, globalHub, f"{houseIndex}_flower", loc,
                                      long)
        kettle = IoTDeviceSmartKettle(env, ips[4], fixedPort, globalHub, f"{houseIndex}_kettle", loc,
                                      long)

        devicesOnThisHouse = [tv, brush, window, flower, kettle]
        allDevices.extend(devicesOnThisHouse)
        allDevicesByHouse[houseIndex] = devicesOnThisHouse

    for houseIndex in range(nhouses):
        allDevicesInThisHouse = allDevicesByHouse[houseIndex]
        for device in allDevicesInThisHouse:
            device.start()


"""
def device_send_metrics(env, device: IoTDevice, hub: IoTHub):
    #
    arrival_time = env.now

    with hub.loggers.request() as request:
        yield request
        yield env.process(hub.log_action(device))

    with hub.metrics.request() as request:
        yield request
        yield env.process(hub.update_metrics_in_database(device))

    if random.choice([True, False]):
        with theater.server.request() as request:
            yield request
            yield env.process(theater.sell_food(moviegoer))

    # Moviegoer heads into the theater
    wait_times.append(env.now - arrival_time)


def run_simulation(env, num_cashiers, num_servers, num_ushers):
    theater = Theater(env, num_cashiers, num_servers, num_ushers)

    for moviegoer in range(3):
        env.process(go_to_movies(env, moviegoer, theater))

    while True:
        yield env.timeout(0.20)  # Wait a bit before generating a new person

        moviegoer += 1
        env.process(go_to_movies(env, moviegoer, theater))


def get_average_wait_time(wait_times):
    average_wait = statistics.mean(wait_times)
    # Pretty print the results
    minutes, frac_minutes = divmod(average_wait, 1)
    seconds = frac_minutes * 60
    return round(minutes), round(seconds)
"""


def main():
    # Setup
    random.seed(42)

    # Run the simulation
    env = simpy.Environment()
    hub = IoTHub(env, num_loggers=3, num_store_metrics=3, num_rules_processors=2)
    hub.start()


    NHOUSES = 1
    generateRandomDeployment(env,
                             hub,
                             nhouses=NHOUSES,
                             center_lat=44.42810022576185,
                             center_long=26.10414240626916)

    """ #Test 
    smart_flower = IoTDeviceSmartFlower(env=env,
                                        IP="127.0.0.1",
                                        Port=5774,
                                        ParentHub=hub,
                                        id="smart_flower",
                                        loc_lat="44.42810022576185",
                                        loc_long="26.10414240626916")
    """

    # env.process(run_simulation(env, num_cashiers, num_servers, num_ushers))
    env.run(until=2500)

    # View the results
    """
    @mins, secs = get_average_wait_time(wait_times)
    print(
        "Running simulation...",
        f"\nThe average wait time is {mins} minutes and {secs} seconds.",
    )
    """


if __name__ == "__main__":
    main()
