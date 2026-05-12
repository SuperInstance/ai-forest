module ptr_mod
  use iso_c_binding
  implicit none
contains
  subroutine write_42(ptr) bind(c, name="write_42")
    type(c_ptr), value :: ptr
    integer(c_int32_t), pointer :: p
    call c_f_pointer(ptr, p)
    p = 42
  end subroutine
end module
