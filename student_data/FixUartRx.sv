// UART 4N1 receiver with 4x oversampling.
//
// Protocol: idle=HIGH. Start bit (LOW), 4 data bits LSB-first, stop bit (HIGH).
// Oversampling: 4 ticks per bit period. Mid-bit sampling at tick 1 gives
// best noise margin (center of the bit).
//
// FSM: IDLE(0) -> START(1) -> DATA(2) -> STOP(3)
// In START: wait for mid-bit (tick 1), confirm rx still LOW, go to DATA.
// In DATA:  sample rx at mid-bit (tick 1), shift into register, 4 bits.
// In STOP:  sample rx at mid-bit (tick 1), if HIGH pulse rx_valid.
//
// Full frame: 1(start) + 4(data) + 1(stop) = 6 bit periods = 24 ticks.
//
// Three bugs corrupt the sampling timing, shift direction, and stop check.
module uart_rx(
  input  clk,
  input  reset,
  input  rx,
  output reg [3:0] rx_data,
  output reg       rx_valid
);
  localparam IDLE  = 2'd0;
  localparam START = 2'd1;
  localparam DATA  = 2'd2;
  localparam STOP  = 2'd3;

  reg [1:0] state;
  reg [1:0] tick_cnt;   // 0..3 for 4x oversampling
  reg [1:0] bit_idx;    // 0..3 for 4 data bits
  reg [3:0] shift;

  initial begin
    state = IDLE; tick_cnt = 0; bit_idx = 0;
    shift = 0; rx_data = 0; rx_valid = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      state    <= IDLE;
      tick_cnt <= 0;
      bit_idx  <= 0;
      shift    <= 0;
      rx_data  <= 0;
      rx_valid <= 0;
    end else begin
      rx_valid <= 1'b0;  // default: no valid pulse

      case (state)
        IDLE: begin
          tick_cnt <= 0;
          bit_idx  <= 0;
          if (rx == 1'b0)              // Start bit detected
            state <= START;
        end

        START: begin
          if (tick_cnt == 2'd1) begin
            tick_cnt <= 0;
            if (rx == 1'b0)
              state <= DATA;           // Confirmed start bit
            else
              state <= IDLE;           // False start
          end else
            tick_cnt <= tick_cnt + 1;
        end

        DATA: begin
          if (tick_cnt == 2'd1) begin
            tick_cnt <= 0;
            shift <= {tick_cnt[1], shift[3:1]};
            if (bit_idx == 2'd3) begin
              state <= STOP;
            end else
              bit_idx <= bit_idx + 1;
          end else
            tick_cnt <= tick_cnt + 1;
        end

        STOP: begin
          if (tick_cnt == 2'd1) begin
            tick_cnt <= 0;
            if (shift[0] == 1'b1) begin
              rx_data  <= {shift[2:0], 1'b0};
              rx_valid <= 1'b1;
            end
            state <= IDLE;
          end else
            tick_cnt <= tick_cnt + 1;
        end
      endcase
    end
  end

  p_reset:       assert property (@(posedge clk) reset |=> state == IDLE && !rx_valid);
  p_valid_pulse: assert property (@(posedge clk) rx_valid |=> !rx_valid);
  p_mid_sample:  assert property (@(posedge clk) !reset && state == START && tick_cnt == 2'd1 && rx == 1'b0 |=> state == DATA);
  p_lsb_first:   assert property (@(posedge clk) !reset && state == DATA && tick_cnt == 2'd1 && bit_idx == 2'd0 |=> shift[3] == $past(rx));
  p_stop_check:  assert property (@(posedge clk) !reset && state == STOP && tick_cnt == 2'd1 && rx == 1'b0 |=> !rx_valid);
  p_byte_val:    assert property (@(posedge clk) rx_valid |-> rx_data == shift);
endmodule
