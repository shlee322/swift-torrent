from swift.common.http import is_success
from swift.common.swob import wsgify
from swift.common.utils import split_path, get_logger
from swift.common import wsgi
import bencode
import hashlib


class TorrentMiddleware(object):

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(conf, log_route='torrent')

        torrent_store_module = conf.get('torrent_store', 'swifttorrent.common.store.swiftaccount:SwiftAccountStore').split(':')
        self._torrent_store = __import__(torrent_store_module[0]).__attr__(torrent_store_module[1])(app, conf)

    def update_torrent_meta_info(self, req, piece_len=None):
        self.logger.debug('update_torrent_meta_info %s' % req.path_info)

        (version, account, container, obj) = split_path(req.path_info, 4, 4, True)

        # TODO : custom default piece_len
        if not piece_len:
            piece_len = 1024*64

        info = self.gen_torrent_meta_info(req, piece_len)
        info_hash = hashlib.sha1(bencode.bencode(info)).hexdigest()

        self._torrent_store.save(
            path=(account, container, obj_path),
            info_hash=info_hash,
            piece_length=piece_len)

    def gen_torrent_meta_info(self, req, piece_len):
        self.logger.debug('get_torrent_meta_info %s' % req.path_info)

        (version, account, container, obj) = split_path(req.path_info, 4, 4, True)

        # Get File Length
        sub = wsgi.make_subrequest(request.environ, method='HEAD')
        meta_resp = sub.get_response(self.app)

        file_length = int(meta_resp.headers['Content-Length'])

        # TODO : Get Pieces
        req_piece = wsgi.make_subrequest(request.environ, method='GET')
        if req_piece.params('torrent', None) is not None:
            del req_piece.params['torrent']

        resp_piece = req_piece.get_response(self.app)

        info = {
            'piece length': piece_len,
            'pieces': 'aa',
            'name': obj,
            'length': meta_resp.headers['Content-Length'],
            'x-swift-account': account,
            'x-swift-container': container,
            'x-swift-object': obj,
        }

        return info

    def get_torrent_info_hash_and_piece_length(self, req):
        (version, account, container, obj) = split_path(req.path_info, 4, 4, True)
        return self._torrent_store.get(['info_hash', 'piece_length'], path=(account, container, obj))

    def response_torrent_file(self, req):
        (version, account, container, obj) = split_path(req.path_info, 4, 4, True)

        piece_len = self._torrent_store.get(['piece_length'], path=(account, container, obj))
        info = self.get_torrent_meta_info(req, piece_len)
        torrent_file = {
            'info': info,
            'announce': 'http://tracker.elab.kr'
        }
        resp = Response(content_type='application/octet-stream')
        resp.body = bencode.bencode(torrent_file)
        return resp

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
                resp = Response()
                resp.status = 400
                resp.body = 'X-Torrent-Piece-Length Error'
                return resp

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
