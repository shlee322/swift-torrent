Openstack Swift Bittorrent Middleware

1. Middleware

swift proxy server에 추가하는 미들웨어입니다.

`obj?torrent`를 통해 torrent 파일을 다운로드 할 수 있게 만들며,
swift object metadata에 info_hash를 추가합니다.

obj의 PUT를 hook하여 torrent info_hash와 해당 obj path 매칭 테이블을

생성하는 역할을 수행합니다. (+ httpseed TODO)


2. Tracker

Bittorrent Client로 부터 Peer List 조회 요청이 오게 되면

peer ring에서 담당 peer server 3개의 IP정보와 다른 클라이언트 정보를

전송합니다. (경우에 따라 다른 클라이언트는 생략 가능합니다)

WSGI로 구현되어 있습니다.


3. Peer

실제 파일 전송을 담당하는 서버입니다.

요청된 info_hash를 담당하는 peer server인 경우 proxy server에 접근하여 파일을 가져오며,

아닌 경우 파일을 찾지 못한다고 결과를 돌려줍니다.

(TCP, UTP 등 확장을 고려해야 함)


기타

기본적으로 peer list, tracker host 관리는 file로 이루어지나

모듈로 되어있어 변경이 가능합니다. (ENV)
