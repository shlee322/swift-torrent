from swift.common.http import is_success
from swift.common.swob import wsgify
from swift.common.utils import split_path, get_logger
import bencode
import hashlib


class TorrentMiddleware(object):

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(conf, log_route='torrent')

    def gen_torrent_meta_info(self, req, res_obj_meta=None):
        (version, account, container, obj) = split_path(req.path_info, 4, 4, True)
        # if HEAD:
        # Call HEAD Content-Length
        # Range Request
        # else: HEAD HEADER
        torrent_meta_info = {
            'info': {
                'piece length': 65536,
                'pieces': 'aa',
                'name': obj,
                'length': 3,
                'x-swift-account': account,
                'x-swift-container': container,
                'x-swift-object': obj,
             },
             'announce': 'http://tracker.elab.kr'
        }

        return torrent_meta_info

    def update_torrent_meta_info(self, req, piece_len=None):
        #self.app
        # Request HEAD -> 
        pass

    def get_torrent_meta_info(self, req):
        (version, account, container, obj) = split_path(req.path_info, 4, 4, True)
        info = {
            'piece length': 65536,
            'pieces': 'aa',
            'name': obj,
            'length': 3,
            'x-swift-account': account,
            'x-swift-container': container,
            'x-swift-object': obj,
        }
        return info

    def get_torrent_info_hash_and_piece_length(self, req):
        info = self.get_torrent_meta_info_dict(req)
        bencode.bencode(info)
        return 'aaaaaaaaaaaaaaaaaa', info['piece length']   # info_hash, Piece Length

    def response_torrent_file(self, req):
        info = self.get_torrent_meta_info(req)
        torrent_file = {
            'info': info,
            'announce': 'http://tracker.elab.kr'
        }
        return None

    @wsgify
    def __call__(self, req):
        obj = None

        try:
            (version, account, container, obj) = split_path(req.path_info, 4, 4, True)
        except ValueError:
            # not an object request
            return req.get_response(self.app)

        # Get object content
        if (req.method == 'GET' and req.params.get('torrent', None) is None) or req.method == 'HEAD':
            resp = req.get_response(self.app)
            if is_success(resp.status_int):
                info_hash, piece_length = self.get_torrent_info_hash_and_piece_length(req)
                resp.headers['X-Torrent-Info-Hash'] = info_hash
                resp.headers['X-Torrent-Piece-Length'] = piece_length
            return resp

        # Request .torrent File
        if req.method == 'GET':
            return self.response_torrent_file(req)

       piece_len = None
       if req.method in ['POST', 'PUT'] and req.headers.get('X-Torrent-Piece-Length'):
            try:
                piece_len = int(req.headers['X-Torrent-Piece-Length'])
            except ValueError:
                return None # Error X-Torrent-Piece-Length Data

        # Call API
        resp = req.get_response(self.app)
        if not is_success(resp.status_int):
            return resp

        # Update Torrent MetaData
        if req.method in ['POST', 'PUT'] and piece_len:
            self.update_torrent_meta_info(req, piece_len)
        elif req.method in ['POST', 'DELETE']:
            self.update_torrent_meta_info(req)

        return resp


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    def torrent_filter(app):
        return TorrentMiddleware(app, conf)
    return torrent_filter
