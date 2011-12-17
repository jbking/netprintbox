"""
    Netprintbox
    Copyright (C) 2011  MURAOKA Yusuke <yusuke@jbking.org>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


class OverLimit(ValueError):
    pass


class TransactionError(Exception):
    pass


class DropboxError(Exception):
    pass


class DropboxBadRequest(DropboxError):
    """Bad input parameter. Error message should indicate which one and why."""


class DropboxUnauthorized(DropboxError):
    """Bad or expired token. This can happen if the user or Dropbox revoked or
       expired an access token. To fix, you should re-authenticate the user."""


class DropboxForbidden(DropboxError):
    """Bad OAuth request (wrong consumer key, bad nonce, expired timestamp...).
       Unfortunately, re-authenticating the user won't help here."""


class DropboxNotFound(DropboxError):
    """File or folder not found at the specified path."""


class DropboxMethodNotAllowed(DropboxError):
    """Request method not expected (generally should be GET or POST)."""


class DropboxServiceUnavailable(DropboxError):
    """Your app is making too many requests and is being rate limited.
       503s can trigger on a per-app or per-user basis."""


class DropboxInsufficientStorage(DropboxError):
    """User is over Dropbox storage quota."""


class DropboxServerError(DropboxError):
    """Server error. Check DropboxOps(http://status.dropbox.com/)"""


class PendingUser(Exception):
    pass


class BecomePendingUser(PendingUser):
    pass


class InvalidNetprintAccountInfo(ValueError):
    pass
