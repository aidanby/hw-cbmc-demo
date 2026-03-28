// Traffic light FSM: RED -> RED_YELLOW -> GREEN -> YELLOW -> RED
// The FSM is not completing the full cycle correctly.
module traffic_light(input clk, input reset, output reg [1:0] state);
  localparam RED        = 2'd0;
  localparam RED_YELLOW = 2'd1;
  localparam GREEN      = 2'd2;
  localparam YELLOW     = 2'd3;

  initial state = RED;
  always @(posedge clk) begin
    if (reset) begin
      state <= RED;
    end else begin
      case (state)
        RED:        state <= RED_YELLOW;
        RED_YELLOW: state <= YELLOW;
        GREEN:      state <= YELLOW;
        YELLOW:     state <= YELLOW;
        default:    state <= RED;
      endcase
    end
  end

  p_valid:       assert property (@(posedge clk) state inside {RED, RED_YELLOW, GREEN, YELLOW});
  p_redy_to_g:   assert property (@(posedge clk) state == RED_YELLOW && !reset |=> state == GREEN);
  p_yellow_to_r: assert property (@(posedge clk) state == YELLOW |=> state == RED);
endmodule
