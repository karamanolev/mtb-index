import io
import os
from itertools import chain
from zipfile import ZipFile

import gpxpy
import requests
import simplejson
from polyline.codec import PolylineCodec
from shapely.geometry.linestring import LineString

exec_root = os.path.dirname(__file__)


def read_json(path):
    with open(path, 'r') as f:
        return simplejson.loads(f.read(), use_decimal=True)


def write_json(path, data, dumps_params):
    value = simplejson.dumps(data, **dumps_params)
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(value)
    return len(value)


def extract_segments_from_gpx(gpx):
    for track in gpx.tracks:
        for segment in track.segments:
            yield segment


def extract_gpxes(cache_path):
    if cache_path.lower().endswith('.gpx'):
        print('Parsing', cache_path)
        with open(cache_path) as f:
            yield gpxpy.parse(f)
    elif cache_path.lower().endswith('.zip'):
        print('Opening ZIP', cache_path)
        z = ZipFile(cache_path)
        for file_info in z.filelist:
            if file_info.filename.lower().endswith('.gpx'):
                print('Parsing', cache_path + '/' + file_info.filename)
                with z.open(file_info) as f:
                    xml = f.read().decode()
                    yield gpxpy.parse(xml)
    else:
        raise Exception('Unsupported file type ' + cache_path)


def get_gpxes(trace_url):
    cache_path = os.path.join(exec_root, 'cache', os.path.basename(trace_url))
    if not os.path.exists(cache_path):
        print('Downloading', trace_url)
        with open(cache_path, 'wb') as f:
            resp = requests.get(trace_url, stream=True)
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=4096):
                f.write(chunk)
    for gpx in extract_gpxes(cache_path):
        yield gpx


def segment_to_polyline(segment):
    points = [(p.latitude, p.longitude) for p in segment.points]
    ls = LineString(points)
    ls = ls.simplify(0.0001)
    return ls.coords


def process_route(route):
    result = dict(route)
    for trace_url in route['traces']:
        polylines = list(map(segment_to_polyline, chain.from_iterable(
            map(extract_segments_from_gpx, get_gpxes(trace_url)))))
    print('Route {0} got {1} polylines, {2} points total'.format(
        route['traces'][0], len(polylines), sum(len(p) for p in polylines)))
    codec = PolylineCodec()
    result['polylines'] = list(map(codec.encode, polylines))
    return result


def main():
    result = {
        'routes': []
    }
    input_data = read_json(os.path.join(exec_root, 'input.json'))
    for route in input_data['routes']:
        result['routes'].append(process_route(route))
    bytes = write_json(os.path.join(exec_root, '../web/routes.json'), result, {
        'ensure_ascii': False,
    })
    print('Wrote {0} routes. {1} bytes per route. {2} bytes total.'.format(
        len(result['routes']), bytes / len(result['routes']), bytes))


if __name__ == '__main__':
    main()
