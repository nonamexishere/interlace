"""Assert roster imported by pipeline/tools/gate_tauri.py."""
from __future__ import annotations

from tauri_gate.scan import (  # noqa: E402
    CSP,
    _chrome_en_text,
)
from tauri_gate.timeline_rows import (  # noqa: E402
    assert_chat_bubbles,
    assert_day_separators,
    assert_local_tz_display,
    assert_gmail_timeline_rows,
)
from tauri_gate.timeline_scroll import (  # noqa: E402
    assert_timeline_latest,
    assert_virtualized_timeline,
    assert_variable_height_timeline,
)
from tauri_gate.timeline_filters import (  # noqa: E402
    assert_timeline_platform_chips,
    assert_timeline_kind_filter,
)
from tauri_gate.timeline_hierarchy import (  # noqa: E402
    assert_timeline_grouped_runs,
    assert_timeline_bubble_hierarchy,
    assert_timeline_attach_slot,
)
from tauri_gate.people_switcher import assert_conversation_switcher  # noqa: E402
from tauri_gate.people_list import (  # noqa: E402
    assert_people_filter_identity,
    assert_people_list_lock,
    assert_people_sidebar_no_x_scroll,
    assert_human_time_people,
)
from tauri_gate.people_collapse import assert_people_sidebar_collapse  # noqa: E402
from tauri_gate.people_inspector import assert_person_inspector  # noqa: E402
from tauri_gate.media_lightbox import (  # noqa: E402
    assert_photo_lightbox,
    assert_voice_note_player,
    assert_voice_note_seek,
)
from tauri_gate.media_cas import assert_cas_video_pdf  # noqa: E402
from tauri_gate.media_linkify import assert_bubble_linkify  # noqa: E402
from tauri_gate.media_bubble import (  # noqa: E402
    assert_bubble_search,
    assert_copy_reveal_cas,
)
from tauri_gate.search_filters import (  # noqa: E402
    assert_search_platform_select,
    assert_search_conversation_kind,
    assert_search_attachment_filter,
)
from tauri_gate.search_field import (  # noqa: E402
    assert_chrome_search_field,
    assert_search_as_you_type,
)
from tauri_gate.search_hits import (  # noqa: E402
    assert_search_jump_to_message,
    assert_search_safe_highlight,
    assert_search_hit_density,
)
from tauri_gate.search_picker import (  # noqa: E402
    assert_search_person_picker,
    assert_search_filters_secondary,
)
from tauri_gate.import_boot import (  # noqa: E402
    assert_boot_spinner,
    assert_first_run,
)
from tauri_gate.import_reveal import (  # noqa: E402
    assert_reveal_archive,
    assert_defer_doctor_cas,
)
from tauri_gate.import_doctor import (  # noqa: E402
    assert_drag_drop_import,
    assert_import_progress,
    assert_import_cancel,
)
from tauri_gate.review import (  # noqa: E402
    assert_review_identifiers,
    assert_review_chrome,
    assert_sidebar_undo_chrome,
)
from tauri_gate.titlebar import (  # noqa: E402
    assert_window_title,
    assert_custom_titlebar,
)
from tauri_gate.locale import (  # noqa: E402
    assert_macos_menu,
    assert_chrome_locale,
    assert_chrome_locale_panes,
)
from tauri_gate.keyboard import (  # noqa: E402
    assert_keyboard_map,
    assert_keyboard_list_arrows,
)
from tauri_gate.palette import (  # noqa: E402
    assert_command_palette,
    assert_command_palette_people_cap,
    assert_command_palette_field_keys,
    assert_command_palette_clipboard,
)
from tauri_gate.density import (  # noqa: E402
    assert_font_density,
    assert_light_chrome,
)
from tauri_gate.reopen_last import assert_reopen_last_session  # noqa: E402
from tauri_gate.window_frame import assert_persist_window_frame  # noqa: E402
from tauri_gate.recent_archives import assert_recent_archives  # noqa: E402
from tauri_gate.recent_archives_fold import assert_recent_archives_fold  # noqa: E402
from tauri_gate.switch_archive import assert_switch_archive  # noqa: E402
from tauri_gate.a11y import (  # noqa: E402
    assert_a11y_listbox_focus_motion,
    assert_focus_aria_audit,
)
from tauri_gate.design import (  # noqa: E402
    assert_design_tokens,
    assert_typography,
    assert_lucide_icons,
)
from tauri_gate.primitives import (  # noqa: E402
    assert_owned_primitives,
    assert_empty_next_action,
    assert_loading_skeletons,
    assert_timeline_append_skeleton_guard,
)
from tauri_gate.contrast import (  # noqa: E402
    assert_contrast_tokens,
    assert_appearance_os,
    assert_status_tokens,
)
from tauri_gate.motion import assert_motion  # noqa: E402
from tauri_gate.status_toasts import (  # noqa: E402
    assert_inflight_audible_status,
    assert_recoverable_toasts,
)
from tauri_gate.status import (  # noqa: E402
    assert_partial_pane_errors,
    assert_partial_retry_generation,
)
from tauri_gate.product_split import assert_product_split  # noqa: E402
